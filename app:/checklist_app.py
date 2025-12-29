# checklist_app.py

from datetime import date, datetime, timedelta
from typing import Optional

import streamlit as st
import streamlit.components.v1 as components

from planner_storage import load_data, save_data


# ---------- Small helpers ----------

def parse_time_str(time_str: str) -> Optional[datetime.time]:
    """Turn 'HH:MM' into a time object, or None if empty/bad."""
    if not time_str:
        return None
    try:
        return datetime.strptime(time_str, "%H:%M").time()
    except ValueError:
        return None


def format_time_display(time_str: str) -> str:
    """Display 'HH:MM' nicely as '7:30 PM' etc."""
    t = parse_time_str(time_str)
    if not t:
        return ""
    return t.strftime("%-I:%M %p")  # e.g. 7:30 PM

def render_task_line_html(t: dict, time_display: str) -> str:
    """Build the visible task line (time • duration • title), styled by done state."""
    pr = t.get("priority", "Medium").lower()
    pr_dot = {"high": "#f97316", "medium": "#eab308", "low": "#22c55e"}.get(pr, "#9ca3af")

    parts = []
    if time_display:
        parts.append(f'<span class="time-pill">{time_display}</span>')
    if t.get("duration", 0):
        parts.append(
            f'<span style="font-size:0.75rem;color:#9ca3af;">{t["duration"]} min</span>'
        )
    parts.append(t["title"])

    line = " • ".join(parts)

    if t.get("done", False):
        # dim + strike when done
        return f'<span style="opacity:0.45;"><s>{line}</s></span>'
    return f"<span>{line}</span>"



def today_iso() -> str:
    return date.today().isoformat()


# ---------- Main app ----------

def main():
    st.set_page_config(
        page_title="Rahil Planner",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Load data once into session_state
    if "data" not in st.session_state:
        st.session_state.data = load_data()

    data = st.session_state.data
    tasks = data["tasks"]
    groups = data["groups"]
    future_me = data["future_me"]

    # --- Custom CSS for dark dashboard style ---
    st.markdown(
        """
        <style>
        body {
            background-color: #020617;
            color: #e5e7eb;
        }
        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 1.5rem;
            max-width: 1200px;
        }
        .card {
            background: #020617;
            border-radius: 16px;
            padding: 1.2rem 1.4rem;
            border: 1px solid #1e293b;
        }
        .card-header {
            font-size: 1.05rem;
            font-weight: 600;
            margin-bottom: 0.8rem;
            color: #e5e7eb;
        }
        .stat-label {
            font-size: 0.8rem;
            color: #9ca3af;
        }
        .stat-value {
            font-size: 1.3rem;
            font-weight: 600;
            color: #facc15;
        }
        .priority-low {
            color: #22c55e;
            font-size: 0.75rem;
        }
        .priority-medium {
            color: #eab308;
            font-size: 0.75rem;
        }
        .priority-high {
            color: #f97316;
            font-size: 0.75rem;
        }
        .time-pill {
            font-size: 0.75rem;
            color: #e5e7eb;
            padding: 2px 8px;
            border-radius: 999px;
            border: 1px solid #1f2937;
            background: #020617;
        }
        </style>
        <script>
        (function() {
            let timeInterval = null;
            
            function formatTime(date) {
                let hours = date.getHours();
                const minutes = date.getMinutes();
                const ampm = hours >= 12 ? 'PM' : 'AM';
                hours = hours % 12;
                hours = hours ? hours : 12;
                const minutesStr = minutes < 10 ? '0' + minutes : minutes;
                return hours + ':' + minutesStr + ' ' + ampm;
            }
            
            function formatDate(date) {
                const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
                const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
                return days[date.getDay()] + ', ' + months[date.getMonth()] + ' ' + date.getDate();
            }
            
            function updateTime() {
                const now = new Date();
                const timeString = formatTime(now);
                const dateString = formatDate(now);
                
                // Update header time
                const headerTimeEl = document.getElementById('header-time-display');
                const headerDateEl = document.getElementById('header-date');
                if (headerTimeEl) headerTimeEl.textContent = timeString;
                if (headerDateEl) headerDateEl.textContent = dateString;
                
                // Update widget time
                const widgetTimeEl = document.getElementById('widget-time');
                if (widgetTimeEl) widgetTimeEl.textContent = timeString;
            }
            
            function startTimeUpdate() {
                if (timeInterval) clearInterval(timeInterval);
                updateTime();
                timeInterval = setInterval(updateTime, 1000);
            }
            
            function tryStart() {
                const headerTimeEl = document.getElementById('header-time-display');
                const widgetTimeEl = document.getElementById('widget-time');
                
                if (headerTimeEl || widgetTimeEl) {
                    startTimeUpdate();
                } else {
                    setTimeout(tryStart, 100);
                }
            }
            
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', tryStart);
            } else {
                setTimeout(tryStart, 300);
            }
            
            // Also try when Streamlit finishes rendering
            window.addEventListener('load', tryStart);
            
            // Listen for Streamlit's frame updates
            const observer = new MutationObserver(function(mutations) {
                const headerTimeEl = document.getElementById('header-time-display');
                const widgetTimeEl = document.getElementById('widget-time');
                if ((headerTimeEl || widgetTimeEl) && !timeInterval) {
                    startTimeUpdate();
                }
            });
            
            observer.observe(document.body, {
                childList: true,
                subtree: true
            });
        })();
        </script>
        """,
        unsafe_allow_html=True,
    )

    # --- Header bar: title + current time + selected day ---
    now = datetime.now()
    initial_time = now.strftime('%I:%M %p')
    initial_date = now.strftime('%A, %b %d')

    header_left, header_right = st.columns([3, 2])

    with header_left:
        st.markdown("### 🧠 Rahil Planner")
        st.caption("Dark-mode daily checklist & schedule — just for you.")

    with header_right:
        st.write("")
        # Time display with auto-update
        st.markdown(
            f'<div id="header-time"><strong>Local time:</strong> <span id="header-date">{initial_date}</span> • <span id="header-time-display">{initial_time}</span></div>',
            unsafe_allow_html=True
        )

    st.markdown("---")

    # --- Sidebar: day + group management ---
    st.sidebar.markdown("### Day")

    selected_date = st.sidebar.date_input(
        "Plan for this day", value=date.today()
    )
    selected_day_iso = selected_date.isoformat()

    # ========== WIDGET SECTION AT TOP ==========
    st.markdown('<div class="card" style="margin-bottom: 1.5rem;">', unsafe_allow_html=True)
    
    # Widget header with time
    widget_header = st.columns([2, 1])
    with widget_header[0]:
        st.markdown("### 🧠 Planner Widget")
    with widget_header[1]:
        st.markdown(
            f'<div id="widget-time" style="text-align: right; color: #9ca3af; font-size: 0.9rem; padding-top: 0.5rem;">{initial_time}</div>',
            unsafe_allow_html=True
        )
    
    # Widget content: Stats + Quick Add + Upcoming
    widget_col1, widget_col2, widget_col3 = st.columns([1, 1, 2])
    
    with widget_col1:
        # Stats
        total = len([t for t in tasks if t["day"] == selected_day_iso])
        completed = len([t for t in tasks if t["day"] == selected_day_iso and t.get("done", False)])
        remaining = total - completed
        
        st.metric("Completed", f"{completed}/{total}", delta=None)
        st.metric("Remaining", remaining, delta=None)
    
    with widget_col2:
        # Quick Add Task
        st.markdown("**Quick Add**")
        with st.form("widget_quick_add", clear_on_submit=True):
            quick_title = st.text_input("Task", key="widget_task", placeholder="Enter task...", label_visibility="collapsed")
            col_time, col_group = st.columns([1, 1])
            with col_time:
                quick_time = st.text_input("Time", key="widget_time", placeholder="14:30", label_visibility="collapsed")
            with col_group:
                quick_group = st.selectbox("Group", groups, key="widget_group", index=0, label_visibility="collapsed")
            
            col_add, col_cancel = st.columns([2, 1])
            with col_add:
                quick_submit = st.form_submit_button("➕ Add", use_container_width=True)
            with col_cancel:
                if st.form_submit_button("✖️", use_container_width=True, help="Clear form"):
                    pass  # Form clears automatically
            
            if quick_submit:
                if not quick_title.strip():
                    st.warning("Task title required")
                else:
                    time_str = quick_time.strip() if quick_time.strip() else ""
                    new_task = {
                        "title": quick_title.strip(),
                        "group": quick_group,
                        "day": selected_day_iso,
                        "time": time_str,
                        "duration": 0,
                        "priority": "Medium",
                        "notes": "",
                        "done": False,
                        "created": datetime.now().isoformat(),
                    }
                    tasks.append(new_task)
                    save_data(data)
                    st.success("✅ Added!")
                    st.rerun()
    
    with widget_col3:
        # Upcoming Events (next 3-4)
        st.markdown("**Upcoming Events**")
        schedule_tasks = [
            t for t in tasks
            if t["day"] == selected_day_iso and t.get("time") and not t.get("done", False)
        ]
        schedule_tasks = sorted(
            schedule_tasks,
            key=lambda t: parse_time_str(t.get("time", "")) or datetime.max.time(),
        )[:4]  # Top 4
        
        if not schedule_tasks:
            st.caption("No upcoming events")
            st.caption("Add tasks with times to see them here")
        else:
            for t in schedule_tasks:
                time_display = format_time_display(t.get("time", ""))
                if not time_display:
                    time_display = t.get("time", "")
                priority = t.get("priority", "Medium").lower()
                priority_color = {"high": "#f97316", "medium": "#eab308", "low": "#22c55e"}.get(priority, "#9ca3af")
                st.markdown(
                    f'<div style="padding: 0.3rem 0; line-height: 1.6;"><span style="color: #3b82f6; font-weight: 600; margin-right: 0.5rem; font-size: 0.85rem;">{time_display}</span>'
                    f'<span style="color: {priority_color}; margin-right: 0.3rem; font-size: 0.7rem;">●</span>'
                    f'<span style="font-size: 0.9rem;">{t["title"]}</span></div>',
                    unsafe_allow_html=True
                )
    
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("---")

    # Copy yesterday's tasks button
    yesterday = selected_date - timedelta(days=1)
    if st.sidebar.button("Copy incomplete from yesterday"):
        copied = 0
        for t in list(tasks):
            if (
                t["day"] == yesterday.isoformat()
                and not t.get("done", False)
            ):
                new_task = t.copy()
                new_task["day"] = selected_day_iso
                new_task["done"] = False
                new_task["created"] = datetime.now().isoformat()
                tasks.append(new_task)
                copied += 1
        if copied:
            save_data(data)
            st.sidebar.success(f"Copied {copied} task(s) from {yesterday.isoformat()}.")
        else:
            st.sidebar.info("No incomplete tasks to copy from yesterday.")

    st.sidebar.markdown("### Groups")

    with st.sidebar.expander("Manage groups", expanded=False):
        st.caption("Add custom categories like 'TRW', 'Gym', 'Side hustle', etc.")
        new_group = st.text_input("New group name", key="new_group_name")
        if st.button("Add group"):
            ng = new_group.strip()
            if ng and ng not in groups:
                groups.append(ng)
                save_data(data)
                st.success(f"Added group: {ng}")
            elif ng in groups:
                st.warning("That group already exists.")
            else:
                st.warning("Group name can't be empty.")

        st.write("**Current groups:**")
        st.write(", ".join(groups))

    # --- Main layout columns ---
    left_col, right_col = st.columns([2, 1])

    # ========== LEFT: Add task + grouped list ==========
    with left_col:
        # --- Add task card ---
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-header">Add a task</div>', unsafe_allow_html=True)

        with st.form("add_task_form", clear_on_submit=True):
            title = st.text_input("Task description")

            group_choice = st.selectbox(
                "Group",
                groups + ["Custom group..."],
            )
            custom_group_name = ""
            if group_choice == "Custom group...":
                custom_group_name = st.text_input("Custom group name")

            # Time + duration + priority + notes
            set_time = st.checkbox("Set time?", value=False)
            time_value = None
            if set_time:
                time_value = st.time_input("Time", value=now.time())

            duration_min = st.number_input(
                "Duration (minutes, optional)",
                min_value=0,
                step=5,
                value=0,
            )

            priority = st.selectbox(
                "Priority",
                ["Low", "Medium", "High"],
                index=1,
            )

            with st.expander("Notes (optional)", expanded=False):
                notes = st.text_area("Notes", height=80)

            submitted = st.form_submit_button("Add to list")

            if submitted:
                if not title.strip():
                    st.warning("Task description can't be empty.")
                else:
                    if group_choice == "Custom group...":
                        group_name = custom_group_name.strip() or "General"
                        if group_name not in groups:
                            groups.append(group_name)
                    else:
                        group_name = group_choice

                    time_str = (
                        time_value.strftime("%H:%M") if time_value else ""
                    )

                    new_task = {
                        "title": title.strip(),
                        "group": group_name,
                        "day": selected_day_iso,
                        "time": time_str,
                        "duration": int(duration_min),
                        "priority": priority,
                        "notes": notes.strip(),
                        "done": False,
                        "created": datetime.now().isoformat(),
                    }
                    tasks.append(new_task)
                    save_data(data)
                    st.success("Task added ✅")

        st.markdown("</div>", unsafe_allow_html=True)

        st.write("")
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(
            f'<div class="card-header">Tasks for {selected_day_iso}</div>',
            unsafe_allow_html=True,
        )

        day_tasks = [t for t in tasks if t["day"] == selected_day_iso]

        if not day_tasks:
            st.info("No tasks yet for this day. Add something above.")
        else:
            # Group then sort: not-done first, then by time
            groups_for_day = sorted({t["group"] for t in day_tasks})

            for g in groups_for_day:
                st.markdown(f"**{g}**")
                group_tasks = [t for t in day_tasks if t["group"] == g]

                # sort
                def sort_key(t):
                    done = t.get("done", False)
                    time_obj = parse_time_str(t.get("time", ""))
                    return (done, time_obj or datetime.max.time())

                group_tasks = sorted(group_tasks, key=sort_key)


                for t in group_tasks:
                    global_idx = tasks.index(t)

                    cols = st.columns([0.08, 0.65, 0.27])

                    # Checkbox
                    with cols[0]:
                        done_val = st.checkbox(
                            "",
                            value=t.get("done", False),
                            key=f"chk-{global_idx}",
                        )

                    # Main text
                    with cols[1]:
                        title_text = t["title"]
                        time_display = format_time_display(t.get("time", ""))

                        # Priority text class
                        pr = t.get("priority", "Medium").lower()
                        pr_class = {
                            "low": "priority-low",
                            "medium": "priority-medium",
                            "high": "priority-high",
                        }.get(pr, "priority-medium")


                        # Build line
                        line_html = render_task_line_html(t, time_display)
                        st.markdown(line_html, unsafe_allow_html=True)
                        if t.get("done", False) and t.get("done_at"):
                            st.markdown(
                                f'<div style="font-size:0.75rem; color:#6b7280; margin-top:2px;">done {t["done_at"]}</div>',
                                unsafe_allow_html=True,
                            )



                        if t.get("notes"):
                            st.caption(t["notes"])

                    # Actions
                    # Actions
                    with cols[2]:
                        # priority badge (keep this)
                        st.markdown(
                            f'<span class="{pr_class}">{t.get("priority", "Medium")} priority</span>',
                            unsafe_allow_html=True,
                        )

                        # Complete / Undo button
                        btn_label = "Undo" if t.get("done", False) else "Complete"
                        if st.button(btn_label, key=f"toggle-{global_idx}"):
                            new_done = not bool(t.get("done", False))
                            tasks[global_idx]["done"] = new_done

                            if new_done:
                                tasks[global_idx]["done_at"] = datetime.now().strftime("%H:%M")
                            else:
                                tasks[global_idx].pop("done_at", None)

                            save_data(data)
                            st.rerun()





            if st.button("Clear all completed tasks for this day"):
                tasks[:] = [
                    t for t in tasks
                    if not (t["day"] == selected_day_iso and t.get("done", False))
                ]
                save_data(data)
                st.rerun()


        st.markdown("</div>", unsafe_allow_html=True)

    # ========== RIGHT: Stats + schedule + Future me ==========
    with right_col:
        # Stats card
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-header">Today\'s stats</div>', unsafe_allow_html=True)

        total = len([t for t in tasks if t["day"] == selected_day_iso])
        completed = len(
            [t for t in tasks if t["day"] == selected_day_iso and t.get("done", False)]
        )
        remaining = total - completed
        pct = (completed / total) if total else 0.0

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown('<span class="stat-label">Completed</span>', unsafe_allow_html=True)
            st.markdown(
                f'<span class="stat-value">{completed}/{total}</span>',
                unsafe_allow_html=True,
            )
        with col_b:
            st.markdown('<span class="stat-label">Remaining</span>', unsafe_allow_html=True)
            st.markdown(
                f'<span class="stat-value">{remaining}</span>',
                unsafe_allow_html=True,
            )

        st.progress(pct)

        st.markdown("</div>", unsafe_allow_html=True)
        st.write("")

        # Upcoming schedule card
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-header">Schedule</div>', unsafe_allow_html=True)

        schedule_tasks = [
            t for t in tasks
            if t["day"] == selected_day_iso and t.get("time")
        ]
        if not schedule_tasks:
            st.info("No timed tasks yet. Set a time on tasks to see them here.")
        else:
            # sort by time
            schedule_tasks = sorted(
                schedule_tasks,
                key=lambda t: parse_time_str(t.get("time", "")) or datetime.max.time(),
            )

            upcoming_lines = []
            for t in schedule_tasks:
                time_display = format_time_display(t.get("time", ""))
                line = f"{time_display} — {t['title']}"
                if t.get("done", False):
                    line = f"~~{line}~~"
                upcoming_lines.append(line)

            for ln in upcoming_lines:
                st.markdown(ln)

            # highlight tasks starting soon (within 60 minutes)
            now_time = now.time()
            soon_min = []
            for t in schedule_tasks:
                t_time = parse_time_str(t.get("time", ""))
                if not t_time or t.get("done", False):
                    continue
                diff = (
                    datetime.combine(date.today(), t_time)
                    - datetime.combine(date.today(), now_time)
                ).total_seconds() / 60.0
                if 0 <= diff <= 60:
                    soon_min.append((t, diff))

            if soon_min:
                st.warning("⏰ Tasks starting within the next hour:")
                for t, diff in soon_min:
                    st.write(f"- {format_time_display(t['time'])} in {int(diff)} min: {t['title']}")

        st.markdown("</div>", unsafe_allow_html=True)
        st.write("")

        # Future me card
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-header">Future me</div>', unsafe_allow_html=True)

        current_note = future_me.get(selected_day_iso, "")
        new_note = st.text_area(
            "Message to future you for this day:",
            value=current_note,
            height=100,
        )

        if st.button("Save note"):
            future_me[selected_day_iso] = new_note.strip()
            save_data(data)
            st.success("Saved your note to future you.")

        st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
