"""Pocket Coach — Complete app (CP1–CP5 + polish).
A Newton School of Technology AI workshop.
"""
import streamlit as st
import db
import prompts
from ai import generate
from datetime import date

db.init_db()
st.set_page_config(page_title="Pocket Coach", page_icon="🤖", layout="centered")

PAGES = ["🏠 Daily check-in", "🔍 See what Gemma saw", "📊 History", "⚙️ Edit goals"]
PERSONAS = ["supportive", "drill_sergeant", "philosopher", "hype_friend"]


# ---------------------------------------------------------------------------
# Setup wizard (first-run only)
# ---------------------------------------------------------------------------
def setup_wizard():
    st.title("Pocket Coach 🤖")
    st.write("Welcome — let's set up your goals.")
    with st.form("setup"):
        ex = st.number_input("Exercise hrs/week", 0, 30, 4)
        sd = st.number_input("Study hrs/week", 0, 60, 15)
        bk = st.number_input("Books/month", 0, 20, 1)
        other = st.text_input("Anything else? (optional)", "")
        persona = st.radio("Coach style", PERSONAS)
        if st.form_submit_button("Save"):
            db.save_goals(ex, sd, bk, persona, other=other)
            st.rerun()


# ---------------------------------------------------------------------------
# CP1 + CP3 + CP4: Daily check-in with 3-step prompt chain
# ---------------------------------------------------------------------------
def daily_check_in():
    goals = db.get_goals()
    st.title("Pocket Coach 🤖")

    # CP5: streak counter
    streak = db.streak_count_ending_today()
    if streak:
        st.caption(f"🔥 {streak}-day streak · Persona: {goals['persona']}")
    else:
        st.caption(f"Persona: {goals['persona']}")

    # Show goals summary
    col1, col2, col3 = st.columns(3)
    col1.metric("🏃 Exercise", f"{goals['exercise_hours_per_week']} hrs/wk")
    col2.metric("📚 Study", f"{goals['study_hours_per_week']} hrs/wk")
    col3.metric("📖 Books", f"{goals['books_per_month']}/month")

    st.divider()

    # CP1: text input area
    today = st.text_area("How was today?", height=100,
                         placeholder="e.g. Studied 3 hours, went for a jog, feeling good...")

    # CP3 + CP4: check-in button → runs 3-step prompt chain
    if st.button("Check in", type="primary", disabled=not today.strip()):
        with st.spinner("Gemma is thinking... (3-step chain)"):
            result = prompts.run_daily_chain(today.strip())

        st.success(result["coach_reply"])

        with st.expander("🔎 Mood + progress breakdown"):
            st.write(f"**Mood:** {result['mood']}")
            st.write(f"**Progress:** {result['progress_summary']}")

    # Quick chat (CP1 original feature preserved)
    st.divider()
    with st.expander("💬 Quick chat with Gemma"):
        prompt = st.text_input("Ask anything:", key="quick_chat")
        if st.button("Send", key="quick_send"):
            if prompt.strip():
                with st.spinner("Thinking..."):
                    reply = generate(prompt)
                st.write(reply)


# ---------------------------------------------------------------------------
# CP4: See what Gemma saw — inspect the prompt chain
# ---------------------------------------------------------------------------
def see_what_gemma_saw():
    st.title("🔍 See what Gemma saw")
    st.caption("Inspect every prompt and response in the chain — full transparency.")

    logs = db.get_recent_logs(10)
    if not logs:
        st.info("No check-ins yet. Go to Daily check-in to get started!")
        return

    for log in logs:
        label = f"{log['log_date']} — {log['user_input'][:60]}"
        with st.expander(label):
            st.write(f"**Your input:** {log['user_input']}")
            if log.get("extracted_mood"):
                st.write(f"**Mood:** {log['extracted_mood']}")
            if log.get("coach_reply"):
                st.write(f"**Coach reply:** {log['coach_reply']}")

            st.divider()
            st.markdown("**Prompt chain steps:**")
            runs = db.get_prompt_runs(log["id"])
            for run in runs:
                st.markdown(f"#### Step: `{run['step_name']}` ({run['ms_elapsed']} ms)")
                st.code(run["prompt_text"], language="text")
                st.markdown(f"**Gemma replied:** {run['response_text']}")


# ---------------------------------------------------------------------------
# Extra: History view — see trends over time
# ---------------------------------------------------------------------------
def history_view():
    st.title("📊 Check-in History")
    logs = db.get_recent_logs(30)
    if not logs:
        st.info("No check-ins yet.")
        return

    for log in logs:
        mood_emoji = "😊" if "positive" in (log.get("extracted_mood") or "").lower() else \
                     "😐" if "neutral" in (log.get("extracted_mood") or "").lower() else \
                     "😔" if "negative" in (log.get("extracted_mood") or "").lower() else "🤔"

        with st.container():
            col1, col2 = st.columns([1, 4])
            with col1:
                st.markdown(f"### {mood_emoji}")
                st.caption(log["log_date"])
            with col2:
                st.write(f"**You said:** {log['user_input']}")
                if log.get("coach_reply"):
                    st.write(f"**Coach:** {log['coach_reply']}")
            st.divider()


# ---------------------------------------------------------------------------
# CP5: Edit goals page
# ---------------------------------------------------------------------------
def edit_goals():
    st.title("⚙️ Edit goals")
    goals = db.get_goals()
    with st.form("edit"):
        ex = st.number_input("Exercise hrs/week", 0, 30, goals["exercise_hours_per_week"])
        sd = st.number_input("Study hrs/week", 0, 60, goals["study_hours_per_week"])
        bk = st.number_input("Books/month", 0, 20, goals["books_per_month"])
        other = st.text_input("Other goal", goals.get("other_goal") or "")
        persona = st.radio(
            "Coach style",
            PERSONAS,
            index=PERSONAS.index(goals["persona"]),
        )
        if st.form_submit_button("Save changes"):
            db.save_goals(ex, sd, bk, persona, other=other)
            st.success("✅ Goals updated!")
            st.rerun()


# ---------------------------------------------------------------------------
# Main — routing
# ---------------------------------------------------------------------------
def main():
    if db.get_goals() is None:
        setup_wizard()
        return

    page = st.sidebar.radio("Page", PAGES)

    if page == "🏠 Daily check-in":
        daily_check_in()
    elif page == "🔍 See what Gemma saw":
        see_what_gemma_saw()
    elif page == "📊 History":
        history_view()
    elif page == "⚙️ Edit goals":
        edit_goals()


if __name__ == "__main__":
    main()
