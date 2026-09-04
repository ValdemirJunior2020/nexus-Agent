import asyncio, json, re
from .config import CONFIG
from .ollama_client import OllamaClient
from .memory import add, recent
from .agents.prompts import ROLES
from .tools.registry import tool_catalog_text, execute as execute_tool

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
        msgs = [{"role":"system","content":system}]
        if context:
            msgs.append({"role":"user","content":"CONTEXT:\n"+context})
        msgs.append({"role":"user","content":task})
        return await self.llm.chat(msgs, model=model, temperature=0.10 if role in ("planner","reviewer","critic","qa","tool_router") else None)

    async def _tool_loop(self, prompt, model, context):
        if not CONFIG.get("agent", {}).get("tool_router_enabled", True):
            return [], ""
        observations=[]
        max_rounds=int(CONFIG.get("agent",{}).get("max_tool_rounds",4))
        catalog=tool_catalog_text()
        for _ in range(max_rounds):
            obs_text="\n\n".join(json.dumps(x,ensure_ascii=False)[:50000] for x in observations)
            routing = await self._call_role(
                "tool_router",
                f"""ORIGINAL USER REQUEST:\n{prompt}\n\nAVAILABLE TOOLS:\n{catalog}\n\nPREVIOUS TOOL OBSERVATIONS:\n{obs_text or '(none)'}\n\nPick the next tool only if it is actually needed.""",
                model,
                context,
            )
            choice=self._extract_json(routing,{"action":"finish","tool":"","args":{},"reason":"router parse fallback"})
            if choice.get("action") != "tool":
                break
            name=str(choice.get("tool","")).strip()
            args=choice.get("args") if isinstance(choice.get("args"),dict) else {}
            if not name:
                break
            result=await execute_tool(name,args,model)
            observations.append({"tool":name,"args":args,"result":result})
        text="\n\n".join(f"[TOOL {o['tool']}]\n{o['result']}" for o in observations)
        return observations,text

    async def run(self, prompt, model=None, session_id="default", mode="auto", context=None, allow_tools=True):
        model = model or CONFIG["ollama"]["default_model"]
        memory = recent(session_id, limit=10)
        memory_text = "\n".join(f'{m["role"]}: {m["content"]}' for m in memory)
        base_context = "\n\n".join(x for x in [memory_text, context or ""] if x).strip()
        add(session_id, "user", prompt)

        tool_observations=[]
        tool_context=""
        if allow_tools and mode != "fast":
            tool_observations,tool_context=await self._tool_loop(prompt,model,base_context)
        full_context="\n\n".join(x for x in [base_context, tool_context] if x).strip()

        if mode == "fast" or not CONFIG["agent"].get("planner_enabled", True):
            answer = await self.llm.chat([
                {"role":"system","content":ROLES["synthesizer"]},
                {"role":"user","content":("CONTEXT:\n"+full_context+"\n\n" if full_context else "")+prompt}
            ], model=model)
            add(session_id, "assistant", answer)
            return {"answer":answer,"model":model,"session_id":session_id,"agents_used":["synthesizer"],"rounds":1,"verified":False,"metadata":{"mode":mode,"tools_used":[o['tool'] for o in tool_observations]}}

        planner_task = f"""USER REQUEST:\n{prompt}\n\nMODE: {mode}\nAvailable context exists: {bool(full_context)}\nTool evidence already collected: {bool(tool_observations)}\nCreate the best specialist plan. Do not overuse agents."""
        raw_plan = await self._call_role("planner", planner_task, model, full_context)
        plan = self._extract_json(raw_plan, {"complexity":"medium","tasks":[{"agent":"analyst","task":prompt},{"agent":"critic","task":"Check assumptions and likely mistakes in the requested task."}],"final_goal":prompt,"needs_tools":False})

        valid = {"researcher","coder","analyst","document","qa","critic"}
        tasks=[]
        for t in plan.get("tasks",[])[:CONFIG["agent"].get("max_subagents",6)]:
            if t.get("agent") in valid and t.get("task"):
                tasks.append(t)
        preferred={"code":"coder","research":"researcher","qa":"qa","document":"document"}.get(mode)
        if preferred and all(t["agent"] != preferred for t in tasks):
            tasks.insert(0,{"agent":preferred,"task":prompt})
            tasks=tasks[:CONFIG["agent"].get("max_subagents",6)]

        async def do_task(t):
            result=await self._call_role(t["agent"],f'Original request: {prompt}\n\nYour assigned task: {t["task"]}',model,full_context)
            return {"agent":t["agent"],"task":t["task"],"result":result}

        findings=await asyncio.gather(*(do_task(t) for t in tasks)) if CONFIG["agent"].get("parallel_subagents",True) else [await do_task(t) for t in tasks]
        evidence="\n\n".join(f'[{x["agent"].upper()}]\nTask: {x["task"]}\nFinding:\n{x["result"]}' for x in findings)
        if tool_context:
            evidence = "[EXECUTED TOOL EVIDENCE]\n"+tool_context+"\n\n"+evidence

        draft=await self._call_role("synthesizer",f"""ORIGINAL REQUEST:\n{prompt}\n\nSPECIALIST + TOOL FINDINGS:\n{evidence}\n\nCreate the final response. Treat actual tool observations as evidence. Do not claim a tool ran unless it appears above. Resolve disagreements and directly fulfill the request.""",model,full_context)

        verified=False; rounds=1; review_data={}
        if CONFIG["agent"].get("review_enabled",True) and mode != "fast":
            max_rounds=min(3,CONFIG["agent"].get("max_rounds",8))
            for _ in range(max_rounds):
                review_raw=await self._call_role("reviewer",f"""ORIGINAL REQUEST:\n{prompt}\n\nDRAFT:\n{draft}\n\nSPECIALIST/TOOL EVIDENCE:\n{evidence}\n\nReview this draft. Any factual claim based on tools must be supported by the observations.""",model,full_context)
                review_data=self._extract_json(review_raw,{"pass":False,"score":0,"problems":["Could not parse reviewer output"],"fix":"Recheck the answer."})
                if review_data.get("pass") and float(review_data.get("score",0)) >= 85:
                    verified=True; break
                correction=review_data.get("fix") or "; ".join(review_data.get("problems",[]))
                draft=await self._call_role("synthesizer",f"""ORIGINAL REQUEST:\n{prompt}\n\nCURRENT DRAFT:\n{draft}\n\nREVIEW PROBLEMS:\n{review_data.get('problems',[])}\n\nCORRECTION INSTRUCTIONS:\n{correction}\n\nRewrite the answer fixing the problems. Do not expose internal reasoning.""",model,full_context)
                rounds += 1

        add(session_id,"assistant",draft)
        return {"answer":draft,"model":model,"session_id":session_id,"agents_used":[x["agent"] for x in findings]+["synthesizer","reviewer"],"rounds":rounds,"verified":verified,"metadata":{"mode":mode,"complexity":plan.get("complexity","unknown"),"review_score":review_data.get("score") if review_data else None,"task_count":len(tasks),"tools_used":[o["tool"] for o in tool_observations],"tool_rounds":len(tool_observations)}}
