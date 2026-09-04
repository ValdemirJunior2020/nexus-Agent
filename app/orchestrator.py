import asyncio
import json
import re
from typing import Any

from .config import CONFIG
from .ollama_client import OllamaClient
from .memory import add, recent, get_engine_session, set_engine_session
from .agents.prompts import ROLES
from .tools.registry import tool_catalog_text, execute as execute_tool
from .engines.deerflow import status as deerflow_status, run as deerflow_run


class SuperAgent:
    def __init__(self):
        self.llm = OllamaClient()

    def _extract_json(self, text, fallback):
        try:
            return json.loads(text)
        except Exception:
            m = re.search(r"\{.*\}", text, re.S)
            if m:
                try:
                    return json.loads(m.group(0))
                except Exception:
                    pass
        return fallback

    async def _call_role(self, role, task, model, context=""):
        system = ROLES[role]
        msgs = [{"role": "system", "content": system}]
        if context:
            msgs.append({"role": "user", "content": "CONTEXT:\n" + context})
        msgs.append({"role": "user", "content": task})
        low_temp_roles = {"planner", "reviewer", "critic", "qa", "tool_router", "engine_router"}
        return await self.llm.chat(
            msgs,
            model=model,
            temperature=0.10 if role in low_temp_roles else None,
        )

    async def _choose_engine(self, prompt: str, model: str, mode: str, requested_engine: str, context: str):
        if requested_engine and requested_engine != "auto":
            return requested_engine, {"requested": True, "reason": "explicit engine request"}
        if not CONFIG.get("agent", {}).get("engine_router_enabled", True):
            default = str(CONFIG.get("agent", {}).get("default_engine", "nexus"))
            return ("nexus" if default == "auto" else default), {"requested": False, "reason": "engine router disabled"}
        if mode == "fast":
            return "ollama", {"requested": False, "reason": "fast mode"}

        raw = await self._call_role(
            "engine_router",
            f"""USER REQUEST:\n{prompt}\n\nREQUEST MODE: {mode}\nChoose the lightest capable execution engine.""",
            model,
            context,
        )
        decision = self._extract_json(raw, {"engine": "nexus", "complexity": "medium", "reason": "router parse fallback"})
        engine = str(decision.get("engine") or "nexus").lower()
        if engine not in {"ollama", "nexus", "deerflow"}:
            engine = "nexus"

        if engine == "deerflow":
            health = await deerflow_status()
            if not health.get("available"):
                fallback = str(CONFIG.get("deerflow", {}).get("fallback_engine", "nexus"))
                if fallback not in {"ollama", "nexus"}:
                    fallback = "nexus"
                decision["deerflow_fallback"] = True
                decision["deerflow_status"] = health
                decision["reason"] = f"{decision.get('reason','')}; DeerFlow unavailable, fell back to {fallback}".strip("; ")
                engine = fallback
        return engine, decision

    async def _tool_loop(self, prompt, model, context):
        if not CONFIG.get("agent", {}).get("tool_router_enabled", True):
            return [], ""
        observations = []
        max_rounds = int(CONFIG.get("agent", {}).get("max_tool_rounds", 4))
        catalog = tool_catalog_text()
        for _ in range(max_rounds):
            obs_text = "\n\n".join(json.dumps(x, ensure_ascii=False)[:50000] for x in observations)
            routing = await self._call_role(
                "tool_router",
                f"""ORIGINAL USER REQUEST:\n{prompt}\n\nAVAILABLE TOOLS:\n{catalog}\n\nPREVIOUS TOOL OBSERVATIONS:\n{obs_text or '(none)'}\n\nPick the next tool only if it is actually needed.""",
                model,
                context,
            )
            choice = self._extract_json(routing, {"action": "finish", "tool": "", "args": {}, "reason": "router parse fallback"})
            if choice.get("action") != "tool":
                break
            name = str(choice.get("tool", "")).strip()
            args = choice.get("args") if isinstance(choice.get("args"), dict) else {}
            if not name:
                break
            result = await execute_tool(name, args, model)
            observations.append({"tool": name, "args": args, "result": result})
        text = "\n\n".join(f"[TOOL {o['tool']}]\n{o['result']}" for o in observations)
        return observations, text

    async def _run_ollama(self, prompt, model, session_id, context, engine_meta):
        answer = await self.llm.chat([
            {"role": "system", "content": ROLES["synthesizer"]},
            {"role": "user", "content": ("CONTEXT:\n" + context + "\n\n" if context else "") + prompt},
        ], model=model)
        add(session_id, "assistant", answer)
        return {
            "answer": answer,
            "model": model,
            "session_id": session_id,
            "agents_used": ["ollama-direct"],
            "rounds": 1,
            "verified": False,
            "metadata": {"mode": "fast", "engine": "ollama", "engine_router": engine_meta, "tools_used": []},
        }

    async def _review_deerflow(self, prompt, answer, model, context):
        raw = await self._call_role(
            "reviewer",
            f"""ORIGINAL REQUEST:\n{prompt}\n\nDEERFLOW DRAFT:\n{answer}\n\nReview this result. Judge whether it fulfills the request and whether it contains unsupported claims or obvious gaps.""",
            model,
            context,
        )
        return self._extract_json(raw, {"pass": False, "score": 0, "problems": ["Could not parse reviewer output"], "fix": "Recheck the answer."})

    async def _run_deerflow(self, prompt, model, session_id, context, deerflow_mode, engine_meta):
        thread_id = get_engine_session(session_id, "deerflow")
        result = await deerflow_run(
            prompt=(f"NEXUS CONTEXT:\n{context}\n\nUSER REQUEST:\n{prompt}" if context else prompt),
            session_id=session_id,
            thread_id=thread_id,
            model=model,
            mode=deerflow_mode,
        )
        if not result.get("ok") and result.get("error") == "thread_not_found":
            result = await deerflow_run(prompt=prompt, session_id=session_id, thread_id=None, model=model, mode=deerflow_mode)
        if not result.get("ok"):
            fallback = str(CONFIG.get("deerflow", {}).get("fallback_engine", "nexus"))
            engine_meta = dict(engine_meta)
            engine_meta["deerflow_runtime_fallback"] = result
            if fallback == "ollama":
                return await self._run_ollama(prompt, model, session_id, context, engine_meta)
            return await self._run_nexus(prompt, model, session_id, "deep", context, True, engine_meta)

        thread_id = result.get("thread_id")
        if thread_id:
            set_engine_session(session_id, "deerflow", str(thread_id))

        answer = str(result.get("answer") or "")
        rounds = 1
        review = await self._review_deerflow(prompt, answer, model, context)
        verified = bool(review.get("pass") and float(review.get("score", 0)) >= 85)

        # If NEXUS catches a weak DeerFlow result, correct it inside the same DeerFlow thread.
        if not verified and thread_id:
            correction = review.get("fix") or "; ".join(review.get("problems", []))
            followup = await deerflow_run(
                prompt=f"""NEXUS FINAL REVIEW FOUND THESE PROBLEMS:\n{review.get('problems', [])}\n\nCORRECTION REQUEST:\n{correction}\n\nPlease correct your previous answer to this original request:\n{prompt}\n\nReturn the improved final answer.""",
                session_id=session_id,
                thread_id=str(thread_id),
                model=model,
                mode=deerflow_mode,
            )
            if followup.get("ok") and followup.get("answer"):
                answer = str(followup["answer"])
                rounds += 1
                review = await self._review_deerflow(prompt, answer, model, context)
                verified = bool(review.get("pass") and float(review.get("score", 0)) >= 85)

        add(session_id, "assistant", answer)
        return {
            "answer": answer,
            "model": model,
            "session_id": session_id,
            "agents_used": ["deerflow", "deerflow-subagents", "nexus-reviewer"],
            "rounds": rounds,
            "verified": verified,
            "metadata": {
                "mode": "deep",
                "engine": "deerflow",
                "deerflow_mode": deerflow_mode,
                "deerflow_thread_id": thread_id,
                "deerflow_run_id": result.get("run_id"),
                "review_score": review.get("score"),
                "engine_router": engine_meta,
            },
        }

    async def _run_nexus(self, prompt, model, session_id, mode, base_context, allow_tools, engine_meta):
        tool_observations = []
        tool_context = ""
        if allow_tools and mode != "fast":
            tool_observations, tool_context = await self._tool_loop(prompt, model, base_context)
        full_context = "\n\n".join(x for x in [base_context, tool_context] if x).strip()

        if mode == "fast" or not CONFIG["agent"].get("planner_enabled", True):
            return await self._run_ollama(prompt, model, session_id, full_context, engine_meta)

        planner_task = f"""USER REQUEST:\n{prompt}\n\nMODE: {mode}\nAvailable context exists: {bool(full_context)}\nTool evidence already collected: {bool(tool_observations)}\nCreate the best specialist plan. Do not overuse agents."""
        raw_plan = await self._call_role("planner", planner_task, model, full_context)
        plan = self._extract_json(raw_plan, {
            "complexity": "medium",
            "tasks": [
                {"agent": "analyst", "task": prompt},
                {"agent": "critic", "task": "Check assumptions and likely mistakes in the requested task."},
            ],
            "final_goal": prompt,
            "needs_tools": False,
        })

        valid = {"researcher", "coder", "analyst", "document", "qa", "critic"}
        tasks = []
        for task in plan.get("tasks", [])[: CONFIG["agent"].get("max_subagents", 6)]:
            if task.get("agent") in valid and task.get("task"):
                tasks.append(task)
        preferred = {"code": "coder", "research": "researcher", "qa": "qa", "document": "document"}.get(mode)
        if preferred and all(t["agent"] != preferred for t in tasks):
            tasks.insert(0, {"agent": preferred, "task": prompt})
            tasks = tasks[: CONFIG["agent"].get("max_subagents", 6)]

        async def do_task(task):
            result = await self._call_role(
                task["agent"],
                f'Original request: {prompt}\n\nYour assigned task: {task["task"]}',
                model,
                full_context,
            )
            return {"agent": task["agent"], "task": task["task"], "result": result}

        if CONFIG["agent"].get("parallel_subagents", True):
            findings = await asyncio.gather(*(do_task(t) for t in tasks))
        else:
            findings = [await do_task(t) for t in tasks]

        evidence = "\n\n".join(f'[{x["agent"].upper()}]\nTask: {x["task"]}\nFinding:\n{x["result"]}' for x in findings)
        if tool_context:
            evidence = "[EXECUTED TOOL EVIDENCE]\n" + tool_context + "\n\n" + evidence

        draft = await self._call_role(
            "synthesizer",
            f"""ORIGINAL REQUEST:\n{prompt}\n\nSPECIALIST + TOOL FINDINGS:\n{evidence}\n\nCreate the final response. Treat actual tool observations as evidence. Do not claim a tool ran unless it appears above. Resolve disagreements and directly fulfill the request.""",
            model,
            full_context,
        )

        verified = False
        rounds = 1
        review_data: dict[str, Any] = {}
        if CONFIG["agent"].get("review_enabled", True) and mode != "fast":
            max_rounds = min(3, CONFIG["agent"].get("max_rounds", 8))
            for _ in range(max_rounds):
                review_raw = await self._call_role(
                    "reviewer",
                    f"""ORIGINAL REQUEST:\n{prompt}\n\nDRAFT:\n{draft}\n\nSPECIALIST/TOOL EVIDENCE:\n{evidence}\n\nReview this draft. Any factual claim based on tools must be supported by the observations.""",
                    model,
                    full_context,
                )
                review_data = self._extract_json(review_raw, {"pass": False, "score": 0, "problems": ["Could not parse reviewer output"], "fix": "Recheck the answer."})
                if review_data.get("pass") and float(review_data.get("score", 0)) >= 85:
                    verified = True
                    break
                correction = review_data.get("fix") or "; ".join(review_data.get("problems", []))
                draft = await self._call_role(
                    "synthesizer",
                    f"""ORIGINAL REQUEST:\n{prompt}\n\nCURRENT DRAFT:\n{draft}\n\nREVIEW PROBLEMS:\n{review_data.get('problems', [])}\n\nCORRECTION INSTRUCTIONS:\n{correction}\n\nRewrite the answer fixing the problems. Do not expose internal reasoning.""",
                    model,
                    full_context,
                )
                rounds += 1

        add(session_id, "assistant", draft)
        return {
            "answer": draft,
            "model": model,
            "session_id": session_id,
            "agents_used": [x["agent"] for x in findings] + ["synthesizer", "reviewer"],
            "rounds": rounds,
            "verified": verified,
            "metadata": {
                "mode": mode,
                "engine": "nexus",
                "engine_router": engine_meta,
                "complexity": plan.get("complexity", "unknown"),
                "review_score": review_data.get("score") if review_data else None,
                "task_count": len(tasks),
                "tools_used": [o["tool"] for o in tool_observations],
                "tool_rounds": len(tool_observations),
            },
        }

    async def run(
        self,
        prompt,
        model=None,
        session_id="default",
        mode="auto",
        context=None,
        allow_tools=True,
        engine="auto",
        deerflow_mode="ultra",
    ):
        model = model or CONFIG["ollama"]["default_model"]
        memory = recent(session_id, limit=10)
        memory_text = "\n".join(f'{m["role"]}: {m["content"]}' for m in memory)
        base_context = "\n\n".join(x for x in [memory_text, context or ""] if x).strip()
        add(session_id, "user", prompt)

        selected_engine, engine_meta = await self._choose_engine(prompt, model, mode, engine, base_context)

        # Explicit DeerFlow still degrades safely if its service is offline.
        if selected_engine == "deerflow":
            health = await deerflow_status()
            if not health.get("available"):
                fallback = str(CONFIG.get("deerflow", {}).get("fallback_engine", "nexus"))
                engine_meta = dict(engine_meta)
                engine_meta["deerflow_status"] = health
                engine_meta["deerflow_fallback"] = True
                selected_engine = fallback if fallback in {"ollama", "nexus"} else "nexus"

        if selected_engine == "ollama":
            return await self._run_ollama(prompt, model, session_id, base_context, engine_meta)
        if selected_engine == "deerflow":
            return await self._run_deerflow(prompt, model, session_id, base_context, deerflow_mode, engine_meta)
        return await self._run_nexus(prompt, model, session_id, mode, base_context, allow_tools, engine_meta)
