"""AuthDesk: Treatment Pre-Authorisation Decision Desk
Interactive Streamlit Application with Step-by-Step Multi-Agent Execution,
Parallel Fan-Out / Fan-In RAG, Peer-Review Escalation, and Live Case Record Inspector.
"""
import streamlit as st
import json
import os
import asyncio
import time
from typing import Dict, Any

from case_record import CaseRecord, create_case
import rag
import llm_client
from orchestrator import execute_step, apply_peer_review, STEPS
from agents import letter_drafter

# Streamlit Page Configuration
st.set_page_config(
    page_title="AuthDesk: Treatment Pre-Authorisation Decision Desk",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(90deg, #6366F1, #38BDF8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 4px;
    }
    .sub-header {
        color: #94A3B8;
        font-size: 1.0rem;
        margin-bottom: 24px;
    }
    .agent-card {
        padding: 16px;
        border-radius: 10px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        background: rgba(30, 41, 59, 0.5);
        margin-bottom: 12px;
    }
    .badge-approve {
        background-color: #065F46;
        color: #34D399;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.9rem;
    }
    .badge-deny {
        background-color: #881337;
        color: #FB7185;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.9rem;
    }
    .badge-moreinfo {
        background-color: #78350F;
        color: #FBBF24;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.9rem;
    }
    .step-active {
        border-left: 4px solid #38BDF8 !important;
        background: rgba(56, 189, 248, 0.08) !important;
    }
    .step-done {
        border-left: 4px solid #34D399 !important;
    }
</style>
""", unsafe_allow_html=True)

# Helper to load test requests
@st.cache_data
def load_test_requests():
    path = os.path.join(os.path.dirname(__file__), "data", "test_requests.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return []

# Initialize Session State
if "case" not in st.session_state:
    st.session_state.case = None
if "current_step" not in st.session_state:
    st.session_state.current_step = -1
if "step_outputs" not in st.session_state:
    st.session_state.step_outputs = {}
if "selected_req_idx" not in st.session_state:
    st.session_state.selected_req_idx = 0
if "peer_review_done" not in st.session_state:
    st.session_state.peer_review_done = False

# Sidebar Controls
st.sidebar.markdown("### ⚙️ Multi-Agent Configuration")
llm_status = "🟢 LLM: " + llm_client.get_model_name() if llm_client.is_llm_available() else "🟡 Mode: Rule-Based Fallback (Offline)"
st.sidebar.info(llm_status)

requests_data = load_test_requests()
req_options = [f"{r['id']}: {r['request'][:55]}..." for r in requests_data] + ["Custom Request Free Text"]

selected_option = st.sidebar.selectbox("Select Pre-Authorisation Referral:", req_options)

if selected_option != "Custom Request Free Text":
    sel_idx = req_options.index(selected_option)
    curr_req = requests_data[sel_idx]
    req_text = curr_req["request"]
    st.sidebar.markdown(f"**Expected Decision:** `{curr_req['expected_decision']}`")
    st.sidebar.markdown(f"**Expected Clauses:** `{'`, `'.join(curr_req['expected_clauses'])}`")
else:
    req_text = st.sidebar.text_area(
        "Enter Raw Clinical Referral:",
        value="Request MRI lumbar spine for patient P-1001. Diagnosis: chronic low back pain for 8 weeks, failed 6 weeks of physiotherapy. Provider: Dr. Rao, City Ortho (in-network). Plan: Gold-500."
    )

st.sidebar.markdown("---")
st.sidebar.markdown("### 🕹️ Execution Controls")

col_btn1, col_btn2, col_btn3 = st.sidebar.columns(3)

def reset_pipeline():
    st.session_state.case = CaseRecord(req_text)
    st.session_state.current_step = -1
    st.session_state.step_outputs = {}
    st.session_state.peer_review_done = False

if col_btn1.button("🔄 Reset", use_container_width=True):
    reset_pipeline()
    st.rerun()

# Auto-initialize if new
if st.session_state.case is None or st.session_state.case.raw_request != req_text:
    reset_pipeline()

auto_play = st.sidebar.checkbox("Auto-play Pipeline", value=False)
speed = st.sidebar.slider("Step Delay (seconds):", min_value=0.2, max_value=2.0, value=0.6, step=0.2) if auto_play else 0.0

if col_btn2.button("⏭️ Next", use_container_width=True, disabled=(st.session_state.current_step >= len(STEPS) - 1 or auto_play)):
    if st.session_state.current_step < len(STEPS) - 1:
        st.session_state.current_step += 1
        st.rerun()

if col_btn3.button("🚀 Run All", use_container_width=True, type="primary"):
    with st.spinner("Executing full multi-agent pipeline..."):
        for s_i in range(len(STEPS)):
            if s_i not in st.session_state.step_outputs:
                title, out = asyncio.run(execute_step(s_i, st.session_state.case))
                st.session_state.step_outputs[s_i] = {"title": title, "data": out}
        st.session_state.current_step = len(STEPS) - 1
    st.rerun()

# Main Header
st.markdown('<div class="main-header">AuthDesk: Treatment Pre-Authorisation Decision Desk</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Collaborative multi-agent utilization management with ChromaDB RAG, parallel fan-out/fan-in, and peer-review escalation.</div>', unsafe_allow_html=True)

# Pipeline Step Progress Indicator
st.markdown("#### 🔄 Agent Coordination Pipeline Flow")
pipe_cols = st.columns(len(STEPS))
for i, step in enumerate(STEPS):
    with pipe_cols[i]:
        if st.session_state.current_step > i:
            st.markdown(f"""<div style="background:rgba(52,211,153,0.12); border:1px solid #34D399; border-radius:8px; padding:8px 6px; text-align:center;">
                <div style="font-weight:700; color:#34D399; font-size:11px;">✓ DONE</div>
                <div style="font-weight:600; font-size:12px; color:#E2E8F0; margin-top:2px;">{i+1}. {step['name']}</div>
            </div>""", unsafe_allow_html=True)
        elif st.session_state.current_step == i:
            st.markdown(f"""<div style="background:linear-gradient(135deg, rgba(34,211,238,0.25), rgba(99,102,241,0.25)); border:2px solid #22D3EE; border-radius:8px; padding:8px 6px; text-align:center; box-shadow:0 0 16px rgba(34,211,238,0.45);">
                <div style="font-weight:800; color:#38BDF8; font-size:11px;">⚡ ACTIVE</div>
                <div style="font-weight:700; font-size:12px; color:#FFFFFF; margin-top:2px;">{i+1}. {step['name']}</div>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""<div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08); border-radius:8px; padding:8px 6px; text-align:center;">
                <div style="font-weight:600; color:#64748B; font-size:11px;">⚪ QUEUED</div>
                <div style="font-weight:500; font-size:12px; color:#94A3B8; margin-top:2px;">{i+1}. {step['name']}</div>
            </div>""", unsafe_allow_html=True)

st.markdown("---")

# Main Working Canvas
left_col, right_col = st.columns([3, 2])

with left_col:
    top_c1, top_c2 = st.columns([3, 1])
    with top_c1:
        st.markdown("### 📋 Active Agent Execution Stage")
    with top_c2:
        if st.button("🚀 Run All Agents", key="run_all_canvas", use_container_width=True, type="primary"):
            with st.spinner("Executing multi-agent pipeline..."):
                for s_i in range(len(STEPS)):
                    if s_i not in st.session_state.step_outputs:
                        title, out = asyncio.run(execute_step(s_i, st.session_state.case))
                        st.session_state.step_outputs[s_i] = {"title": title, "data": out}
                st.session_state.current_step = len(STEPS) - 1
            st.rerun()
    
    # Run active step if needed
    curr_s = st.session_state.current_step
    case = st.session_state.case
    
    if curr_s == -1:
        st.info("👋 Referral loaded into shared memory. Press **'Next Step ⏭️'** or check **'Auto-play'** to begin execution.")
        st.markdown(f"**Raw Referral:**\n> {case.raw_request}")
        
    elif curr_s >= 0:
        # Check if active step needs execution
        if curr_s not in st.session_state.step_outputs:
            with st.spinner(f"Running Agent: {STEPS[curr_s]['name']}..."):
                title, out = asyncio.run(execute_step(curr_s, case))
                st.session_state.step_outputs[curr_s] = {"title": title, "data": out}
        
        # Render all completed steps up to current
        for s_idx in range(curr_s + 1):
            s_meta = STEPS[s_idx]
            s_out = st.session_state.step_outputs.get(s_idx, {})
            
            is_active = (s_idx == curr_s)
            
            with st.container():
                if is_active:
                    st.markdown(f"""
                    <div style="background: linear-gradient(90deg, rgba(34, 211, 238, 0.15), rgba(99, 102, 241, 0.15)); border: 2px solid #22d3ee; border-radius: 12px; padding: 14px 18px; margin-bottom: 12px; box-shadow: 0 0 20px rgba(34, 211, 238, 0.35);">
                      <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 1.15rem; font-weight: 800; color: #38bdf8;">⚡ Step {s_idx + 1}: {s_meta['name']}</span>
                        <span style="background: #0284c7; color: #ffffff; padding: 3px 12px; border-radius: 20px; font-weight: 700; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; box-shadow: 0 0 10px #38bdf8;">● ACTIVE AGENT</span>
                      </div>
                      <div style="color: #cbd5e1; font-size: 0.85rem; margin-top: 4px;">{s_meta['desc']}</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div style="background: rgba(30, 41, 59, 0.4); border: 1px solid rgba(52, 211, 153, 0.4); border-left: 4px solid #34d399; border-radius: 10px; padding: 10px 16px; margin-bottom: 12px;">
                      <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 1.05rem; font-weight: 700; color: #e2e8f0;">✓ Step {s_idx + 1}: {s_meta['name']}</span>
                        <span style="background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid #10b981; padding: 2px 10px; border-radius: 20px; font-weight: 600; font-size: 0.75rem;">COMPLETED</span>
                      </div>
                      <div style="color: #64748b; font-size: 0.82rem; margin-top: 2px;">{s_meta['desc']}</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Render Step 0: Parser
                if s_idx == 0:
                    p = case.get("parsed", {})
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Treatment", p.get("treatment", "-"))
                    c2.metric("Diagnosis", p.get("diagnosis", "-"))
                    c3.metric("Provider", p.get("provider", "-"))
                    c4.metric("Plan", p.get("plan", "-"))
                
                # Render Step 1: Parallel RAG
                elif s_idx == 1:
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown("**Coverage Retrieval Findings (Plan Documents)**")
                        cov = case.get("coverage_findings", {})
                        st.write(f"Status: `{cov.get('status')}`")
                        st.write(f"Cited Clauses: `{cov.get('clauses')}`")
                        st.caption(cov.get("reason", ""))
                    with c2:
                        st.markdown("**Medical Necessity Findings (Clinical Guidelines)**")
                        nec = case.get("necessity_findings", {})
                        st.write(f"Status: `{nec.get('status')}`")
                        st.write(f"Cited Guidelines: `{nec.get('clauses')}`")
                        st.caption(nec.get("reason", ""))

                # Render Step 2: Authorisation Manager
                elif s_idx == 2:
                    dec = case.get("decision", "PENDING")
                    conf = case.get("confidence", 0.0)
                    cited = case.get("cited_clauses", [])
                    
                    b_class = "badge-approve" if dec == "APPROVE" else ("badge-deny" if dec == "DENY" else "badge-moreinfo")
                    st.markdown(f"**Triage Decision:** <span class='{b_class}'>{dec}</span> (Confidence: {int(conf*100)}%)", unsafe_allow_html=True)
                    st.markdown(f"**Supporting Policy Clauses:** `{'`, `'.join(cited)}`")

                # Render Step 3: Peer Review
                elif s_idx == 3:
                    hr = case.get("human_review", {})
                    dec = case.get("decision")
                    
                    if case.get("ai_decision") != "APPROVE" and not hr.get("verdict"):
                        st.warning("⚠️ **Peer Review Escalation Triggered**: Non-approval requires licensed clinical review before letter drafting.")
                        
                        r_col1, r_col2 = st.columns([1, 1])
                        reviewer_name = r_col1.text_input("Reviewer Name & Credential:", value="Dr. Sarah Jenkins, MD (Chief Medical Officer)")
                        review_notes = r_col2.text_input("Review Justification Notes:", value="Policy exclusion / clinical criteria confirmed.")
                        
                        btn_col1, btn_col2, btn_col3 = st.columns(3)
                        if btn_col1.button("👍 Uphold AI Denial", use_container_width=True):
                            asyncio.run(apply_peer_review(case, "UPHOLD", reviewer_name, review_notes))
                            st.session_state.peer_review_done = True
                            st.rerun()
                        if btn_col2.button("🔄 Overturn to Approval", use_container_width=True):
                            asyncio.run(apply_peer_review(case, "OVERTURN", reviewer_name, review_notes))
                            st.session_state.peer_review_done = True
                            st.rerun()
                        if btn_col3.button("📝 Request Info", use_container_width=True):
                            asyncio.run(apply_peer_review(case, "REQUEST_INFO", reviewer_name, review_notes))
                            st.session_state.peer_review_done = True
                            st.rerun()
                    else:
                        if hr.get("verdict"):
                            st.success(f"✅ **Peer Review Signed Off:** `{hr.get('verdict')}` by {hr.get('reviewer')}")
                            st.caption(f"Clinician Notes: {hr.get('notes')}")
                        else:
                            st.info("Straight-through approval: No peer escalation required.")

                # Render Step 4: Letter Drafter
                elif s_idx == 4:
                    st.markdown("**Formal Determination Letter:**")
                    st.text_area("Generated Letter Preview:", value=case.get("letter", ""), height=180, disabled=True)

                # Render Step 5: Final Determination
                elif s_idx == 5:
                    final_dec = case.get("decision")
                    b_class = "badge-approve" if final_dec == "APPROVE" else ("badge-deny" if final_dec == "DENY" else "badge-moreinfo")
                    st.success("🎉 Multi-Agent Pipeline Execution Completed Successfully!")
                    st.markdown(f"**Final Status:** `{case.get('status')}` | **Final Decision:** <span class='{b_class}'>{final_dec}</span>", unsafe_allow_html=True)

                st.markdown("---")

    # Handle auto-play progression
    if auto_play and st.session_state.current_step < len(STEPS) - 1:
        # Pause at peer review if not completed
        if st.session_state.current_step == 2 and case.get("decision") != "APPROVE" and not case.get("human_review", {}).get("verdict"):
            pass  # Wait for human input
        else:
            time.sleep(speed)
            st.session_state.current_step += 1
            st.rerun()

with right_col:
    st.markdown("### 🗄️ Shared Case Record (Live Provenance)")
    st.caption("Every agent reads and writes this single JSON record. Each update logs `{field, value, written_by, timestamp}`.")
    
    # Audit trail table
    if case and case.history:
        st.markdown("#### 📜 Audit History Trail")
        table_rows = []
        for h in case.history:
            val_str = str(h["value"])
            if len(val_str) > 40: val_str = val_str[:37] + "..."
            table_rows.append({
                "Timestamp": h["timestamp"],
                "Written By": h["written_by"],
                "Field": h["field"],
                "Value": val_str
            })
        st.dataframe(table_rows, use_container_width=True, hide_index=True)
    
    # Expandable raw JSON viewer
    with st.expander("🔍 View Complete JSON Case Record", expanded=True):
        st.json(case.to_dict() if case else {})
    
    # Download Case Record JSON
    if case:
        st.download_button(
            label="💾 Download Case Record (.json)",
            data=json.dumps(case.to_dict(), indent=2),
            file_name=f"case_{case.case_id}.json",
            mime="application/json",
            use_container_width=True
        )

