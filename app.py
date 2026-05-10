# Pocket Coach — starter file
# A Newton School of Technology AI workshop.
#
# Each `# TODO (CPn)` block marks where you'll add code during checkpoint n.
# Don't delete the markers — they're your map. If you fall behind, copy the
# matching solutions/CPn/app.py over this file and keep going.

import streamlit as st
import db
from ai import generate

db.init_db()
st.set_page_config(page_title="Pocket Coach", page_icon="🤖")
st.title("Pocket Coach 🤖")

# ---------------------------------------------------------------------------
# CP1: text input + Send button → call generate() → display reply
# ---------------------------------------------------------------------------

prompt = st.text_input("Say hi to Gemma:")
if st.button("Send"):
    with st.spinner("Thinking..."):
        reply = generate(prompt)
    st.write(reply)

# ---------------------------------------------------------------------------
# CP2: setup wizard on first run, welcome back on reruns
# ---------------------------------------------------------------------------

goals = db.get_goals()
if goals is None:
    with st.form("setup"):
        ex = st.number_input("Exercise hrs/week", 0, 30, 4)
        sd = st.number_input("Study hrs/week", 0, 60, 15)
        bk = st.number_input("Books/month", 0, 20, 1)
        persona = st.radio(
            "Coach style",
            ["supportive", "drill_sergeant", "philosopher", "hype_friend"],
        )
        if st.form_submit_button("Save"):
            db.save_goals(ex, sd, bk, persona)
            st.rerun()
else:
    st.success(f"Welcome back! Persona: {goals['persona']}")
    st.write(f"Exercise: {goals['exercise_hours_per_week']} hrs/wk")
    st.write(f"Study: {goals['study_hours_per_week']} hrs/wk")
    st.write(f"Books: {goals['books_per_month']}/month")

# ---------------------------------------------------------------------------
# TODO (CP3): add a "How was today?" text area and a "Check in" button that
#             calls generate() with a goal-aware prompt and saves a row to
#             daily_logs + prompt_runs.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# TODO (CP4): replace the single prompt above with prompts.run_daily_chain()
#             and add a "🔍 See what Gemma saw" sidebar page that lists
#             rows from prompt_runs.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# TODO (CP5): pick ONE polish — streak counter, persona swap, edit-goals
#             page, or your own tweak. Then commit and push to your fork.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Extra mile (stretch — only if you finish CP5 early):
#             Use Open Design (https://github.com/nexu-io/open-design) to
#             generate a v2 mock for your app and commit it to docs/v2-vision.md.
#             See the README's "Extra mile" section.
# ---------------------------------------------------------------------------
