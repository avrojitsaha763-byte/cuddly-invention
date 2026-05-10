"""Pocket Coach — Full-featured app (CP1–CP5 + all enhancements).
A Newton School of Technology AI workshop.
"""
import streamlit as st
import db
import prompts
import pandas as pd
import csv
import io
from ai import generate
from datetime import date, datetime, timedelta

db.init_db()
st.set_page_config(page_title="Pocket Coach", page_icon="🤖", layout="centered")

PAGES = [
    "🏠 Daily check-in",
    "💬 Chat with Coach",
    "📈 Mood & Trends",
    "📊 Weekly Insights",
    "🏆 Achievements",
    "🔍 See what Gemma saw",
    "📋 History & Export",
    "⚙️ Edit goals",
]
PERSONAS = ["supportive", "drill_sergeant", "philosopher", "hype_friend"]

PERSONA_SAMPLES = {
    "supportive": "Hey, that's really great progress! Even small steps matter. Keep going — I believe in you! 💪",
    "drill_sergeant": "Four hours? That's a START, not a finish! You set a target — now HIT it. No excuses tomorrow!",
    "philosopher": "Consider this: every hour of study is a conversation with your future self. What will you say to them?",
    "hype_friend": "YOOO 4 hours of study?! That's INSANE!! You're literally on FIRE right now!! 🔥🔥🔥",
}

ACHIEVEMENT_DEFS = [
    ("🌱 First Steps", "Complete your first check-in", 1),
    ("📅 Three-Peat", "Check in 3 days", 3),
    ("🔥 Week Warrior", "Check in 7 days", 7),
    ("⚡ Fortnight Force", "Check in 14 days", 14),
    ("🏅 Monthly Master", "Check in 30 days", 30),
    ("💎 Fifty Faithful", "Check in 50 days", 50),
    ("👑 Century Champion", "Check in 100 days", 100),
]


def _parse_mood_label(mood_str: str) -> str:
    if not mood_str:
        return "unknown"
    low = mood_str.lower()
    for m in ["positive", "negative", "neutral", "mixed"]:
        if m in low:
            return m
    return "unknown"


def _mood_emoji(mood_str: str) -> str:
    label = _parse_mood_label(mood_str)
    return {"positive": "😊", "neutral": "😐", "negative": "😔", "mixed": "🤔"}.get(label, "❓")


def _mood_score(mood_str: str) -> float:
    label = _parse_mood_label(mood_str)
    return {"positive": 3, "neutral": 2, "negative": 1, "mixed": 2}.get(label, 2)


# ---------------------------------------------------------------------------
# Setup wizard
# ---------------------------------------------------------------------------
def setup_wizard():
    st.title("Pocket Coach 🤖")
    st.write("Welcome — let's set up your goals.")

    st.subheader("🎭 Persona preview")
    preview_tabs = st.tabs(PERSONAS)
    for tab, p in zip(preview_tabs, PERSONAS):
        with tab:
            st.info(PERSONA_SAMPLES[p])

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
# Daily check-in (CP1+CP3+CP4+CP5)
# ---------------------------------------------------------------------------
def daily_check_in():
    goals = db.get_goals()
    st.title("Pocket Coach 🤖")

    streak = db.streak_count_ending_today()
    if streak:
        st.caption(f"🔥 {streak}-day streak · Persona: {goals['persona']}")
    else:
        st.caption(f"Persona: {goals['persona']}")

    col1, col2, col3 = st.columns(3)
    col1.metric("🏃 Exercise", f"{goals['exercise_hours_per_week']} hrs/wk")
    col2.metric("📚 Study", f"{goals['study_hours_per_week']} hrs/wk")
    col3.metric("📖 Books", f"{goals['books_per_month']}/month")
    st.divider()

    today = st.text_area("How was today?", height=100,
                         placeholder="e.g. Studied 3 hours, went for a jog, feeling good...")

    if st.button("Check in", type="primary", disabled=not today.strip()):
        with st.spinner("Gemma is thinking... (3-step chain)"):
            result = prompts.run_daily_chain(today.strip())
        st.success(result["coach_reply"])
        with st.expander("🔎 Mood + progress breakdown"):
            st.write(f"**Mood:** {result['mood']}")
            st.write(f"**Progress:** {result['progress_summary']}")

    st.divider()
    with st.expander("💬 Quick chat with Gemma"):
        prompt = st.text_input("Ask anything:", key="quick_chat")
        if st.button("Send", key="quick_send"):
            if prompt.strip():
                with st.spinner("Thinking..."):
                    reply = generate(prompt)
                st.write(reply)


# ---------------------------------------------------------------------------
# Multi-turn Chat
# ---------------------------------------------------------------------------
def chat_page():
    goals = db.get_goals()
    st.title("💬 Chat with Coach")
    st.caption(f"Chatting as: {goals['persona']}")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    user_input = st.chat_input("Type a message...")
    if user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.write(user_input)

        history_text = "\n".join(
            f"{m['role'].title()}: {m['content']}" for m in st.session_state.chat_history[-6:]
        )
        system_prompt = (
            f"You are a {goals['persona']} lifestyle coach. "
            f"The student aims for {goals['exercise_hours_per_week']}h exercise/week, "
            f"{goals['study_hours_per_week']}h study/week, {goals['books_per_month']} books/month.\n\n"
            f"Conversation so far:\n{history_text}\n\n"
            f"Reply in 2-3 sentences, fully in character as a {goals['persona']}."
        )

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                reply = generate(system_prompt)
            st.write(reply)
        st.session_state.chat_history.append({"role": "assistant", "content": reply})

    if st.session_state.chat_history:
        if st.sidebar.button("🗑️ Clear chat"):
            st.session_state.chat_history = []
            st.rerun()


# ---------------------------------------------------------------------------
# Mood & Trends + Calendar Heatmap
# ---------------------------------------------------------------------------
def mood_trends():
    st.title("📈 Mood & Trends")
    logs = db.get_recent_logs(60)

    if len(logs) < 2:
        st.info("Need at least 2 check-ins to show trends. Keep checking in!")
        return

    # Mood line chart
    st.subheader("Mood over time")
    chart_data = []
    for log in reversed(logs):
        chart_data.append({
            "Date": log["log_date"],
            "Mood Score": _mood_score(log.get("extracted_mood")),
        })
    df = pd.DataFrame(chart_data)
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.set_index("Date")
    st.line_chart(df, y="Mood Score", use_container_width=True)
    st.caption("Scale: 😔 Negative=1 · 😐 Neutral=2 · 🤔 Mixed=2 · 😊 Positive=3")

    # Mood distribution
    st.subheader("Mood distribution")
    mood_counts = {}
    for log in logs:
        label = _parse_mood_label(log.get("extracted_mood"))
        emoji = _mood_emoji(log.get("extracted_mood"))
        key = f"{emoji} {label}"
        mood_counts[key] = mood_counts.get(key, 0) + 1
    dist_df = pd.DataFrame(list(mood_counts.items()), columns=["Mood", "Count"])
    st.bar_chart(dist_df.set_index("Mood"))

    # Calendar heatmap
    st.subheader("📅 Check-in Calendar")
    _render_calendar_heatmap(logs)


def _render_calendar_heatmap(logs):
    log_dates = {}
    for log in logs:
        d = log["log_date"]
        mood = _parse_mood_label(log.get("extracted_mood"))
        log_dates[d] = mood

    today = date.today()
    start = today - timedelta(days=83)  # ~12 weeks

    colors = {
        "positive": "#22c55e", "neutral": "#facc15",
        "negative": "#ef4444", "mixed": "#a78bfa",
        "unknown": "#6b7280", "empty": "#1e1e2e",
    }

    cells = []
    current = start
    while current <= today:
        iso = current.isoformat()
        mood = log_dates.get(iso, "empty")
        color = colors[mood]
        title = f"{iso}: {mood}" if mood != "empty" else iso
        cells.append(f'<div title="{title}" style="width:14px;height:14px;background:{color};'
                     f'border-radius:2px;display:inline-block;margin:1px;"></div>')
        current += timedelta(days=1)

    # Arrange in rows of 7 (weeks)
    rows = []
    for i in range(0, len(cells), 7):
        rows.append("".join(cells[i:i+7]))

    html = (
        '<div style="font-family:monospace;line-height:0;">'
        + "<br>".join(rows)
        + '</div>'
        + '<div style="margin-top:8px;font-size:12px;">'
        + ' '.join(f'<span style="color:{c}">■</span> {k}' for k, c in colors.items() if k != "empty")
        + '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Weekly Insights (AI-generated)
# ---------------------------------------------------------------------------
def weekly_insights():
    st.title("📊 Weekly Insights")
    goals = db.get_goals()
    logs = db.get_recent_logs(7)

    if not logs:
        st.info("No check-ins this week yet. Come back after a few check-ins!")
        return

    st.write(f"**Analyzing your last {len(logs)} check-ins...**")

    log_summary = "\n".join(
        f"- {l['log_date']}: \"{l['user_input']}\" (mood: {l.get('extracted_mood', 'unknown')})"
        for l in logs
    )

    if st.button("🧠 Generate Weekly Report", type="primary"):
        insight_prompt = (
            f"You are an insightful {goals['persona']} lifestyle coach. "
            f"Analyze this student's week and provide a comprehensive report.\n\n"
            f"Goals:\n"
            f"- Exercise: {goals['exercise_hours_per_week']} hrs/week\n"
            f"- Study: {goals['study_hours_per_week']} hrs/week\n"
            f"- Books: {goals['books_per_month']}/month\n"
            f"- Other: {goals.get('other_goal', 'none')}\n\n"
            f"This week's check-ins:\n{log_summary}\n\n"
            f"Provide:\n"
            f"1. **Overall Assessment** (2-3 sentences)\n"
            f"2. **What went well** (bullet points)\n"
            f"3. **Areas to improve** (bullet points)\n"
            f"4. **Specific tip for next week** (1-2 sentences)\n"
            f"5. **Motivational closer** (1 sentence, fully in character as {goals['persona']})\n"
        )
        with st.spinner("Gemma is analyzing your week..."):
            report = generate(insight_prompt)
        st.markdown(report)

    # Quick stats
    st.divider()
    st.subheader("Quick Stats")
    col1, col2, col3 = st.columns(3)
    col1.metric("Check-ins", len(logs))
    positive = sum(1 for l in logs if "positive" in (_parse_mood_label(l.get("extracted_mood")) or ""))
    col2.metric("😊 Positive days", positive)
    col3.metric("🔥 Current streak", db.streak_count_ending_today())


# ---------------------------------------------------------------------------
# Achievements
# ---------------------------------------------------------------------------
def achievements_page():
    st.title("🏆 Achievements")
    total_logs = len(db.get_recent_logs(999))
    streak = db.streak_count_ending_today()

    st.metric("Total check-ins", total_logs)
    st.metric("Current streak", f"🔥 {streak} days")
    st.divider()

    for emoji_name, desc, threshold in ACHIEVEMENT_DEFS:
        unlocked = total_logs >= threshold
        if unlocked:
            st.success(f"**{emoji_name}** — {desc} ✅")
        else:
            remaining = threshold - total_logs
            st.markdown(
                f"🔒 **{emoji_name}** — {desc} "
                f"({remaining} more check-in{'s' if remaining != 1 else ''} needed)"
            )

    # Streak achievements
    st.divider()
    st.subheader("🔥 Streak Achievements")
    streak_badges = [
        ("3-Day Fire", 3), ("7-Day Inferno", 7),
        ("14-Day Blaze", 14), ("30-Day Legend", 30),
    ]
    for name, req in streak_badges:
        if streak >= req:
            st.success(f"**🔥 {name}** — {req}-day streak ✅")
        else:
            st.markdown(f"🔒 **🔥 {name}** — Need {req}-day streak (current: {streak})")


# ---------------------------------------------------------------------------
# See what Gemma saw (CP4)
# ---------------------------------------------------------------------------
def see_what_gemma_saw():
    st.title("🔍 See what Gemma saw")
    st.caption("Inspect every prompt and response in the chain.")
    logs = db.get_recent_logs(10)
    if not logs:
        st.info("No check-ins yet.")
        return
    for log in logs:
        with st.expander(f"{log['log_date']} — {log['user_input'][:60]}"):
            st.write(f"**Your input:** {log['user_input']}")
            if log.get("extracted_mood"):
                st.write(f"**Mood:** {log['extracted_mood']}")
            if log.get("coach_reply"):
                st.write(f"**Coach reply:** {log['coach_reply']}")
            st.divider()
            for run in db.get_prompt_runs(log["id"]):
                st.markdown(f"#### Step: `{run['step_name']}` ({run['ms_elapsed']} ms)")
                st.code(run["prompt_text"], language="text")
                st.markdown(f"**Gemma replied:** {run['response_text']}")


# ---------------------------------------------------------------------------
# History + CSV Export
# ---------------------------------------------------------------------------
def history_export():
    st.title("📋 History & Export")
    logs = db.get_recent_logs(100)
    if not logs:
        st.info("No check-ins yet.")
        return

    # CSV export
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=[
        "log_date", "user_input", "extracted_mood", "progress_summary", "coach_reply", "created_at"
    ])
    writer.writeheader()
    for log in logs:
        writer.writerow({k: log.get(k, "") for k in writer.fieldnames})

    st.download_button(
        "📤 Download CSV",
        output.getvalue(),
        file_name=f"pocket_coach_export_{date.today().isoformat()}.csv",
        mime="text/csv",
    )

    st.divider()
    for log in logs:
        emoji = _mood_emoji(log.get("extracted_mood"))
        with st.container():
            col1, col2 = st.columns([1, 5])
            with col1:
                st.markdown(f"### {emoji}")
                st.caption(log["log_date"])
            with col2:
                st.write(f"**You said:** {log['user_input']}")
                if log.get("coach_reply"):
                    st.write(f"**Coach:** {log['coach_reply']}")
            st.divider()


# ---------------------------------------------------------------------------
# Edit goals (CP5) + persona preview
# ---------------------------------------------------------------------------
def edit_goals():
    st.title("⚙️ Edit goals")
    goals = db.get_goals()

    st.subheader("🎭 Persona preview")
    preview_tabs = st.tabs(PERSONAS)
    for tab, p in zip(preview_tabs, PERSONAS):
        with tab:
            st.info(PERSONA_SAMPLES[p])

    with st.form("edit"):
        ex = st.number_input("Exercise hrs/week", 0, 30, goals["exercise_hours_per_week"])
        sd = st.number_input("Study hrs/week", 0, 60, goals["study_hours_per_week"])
        bk = st.number_input("Books/month", 0, 20, goals["books_per_month"])
        other = st.text_input("Other goal", goals.get("other_goal") or "")
        persona = st.radio(
            "Coach style", PERSONAS,
            index=PERSONAS.index(goals["persona"]),
        )
        if st.form_submit_button("Save changes"):
            db.save_goals(ex, sd, bk, persona, other=other)
            st.success("✅ Goals updated!")
            st.rerun()


# ---------------------------------------------------------------------------
# Main routing
# ---------------------------------------------------------------------------
def main():
    if db.get_goals() is None:
        setup_wizard()
        return

    page = st.sidebar.radio("Page", PAGES)

    if page == "🏠 Daily check-in":
        daily_check_in()
    elif page == "💬 Chat with Coach":
        chat_page()
    elif page == "📈 Mood & Trends":
        mood_trends()
    elif page == "📊 Weekly Insights":
        weekly_insights()
    elif page == "🏆 Achievements":
        achievements_page()
    elif page == "🔍 See what Gemma saw":
        see_what_gemma_saw()
    elif page == "📋 History & Export":
        history_export()
    elif page == "⚙️ Edit goals":
        edit_goals()


if __name__ == "__main__":
    main()
