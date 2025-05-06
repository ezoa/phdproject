

from streamlit_webrtc import webrtc_streamer, VideoProcessorBase
import av
import datetime
import os
import cv2

import streamlit as st
import time
import random
import json
import pandas as pd
from collections import defaultdict
from pathlib import Path

# Layout columns
col1, col2 = st.columns([3, 1])  # Adjust the ratio as needed

with col1:
    # ————————————— Load & Group Questions —————————————————
    QUESTIONS_PATH = Path(__file__).parent / "dataset.json"
    with open(QUESTIONS_PATH, "r", encoding="utf-8") as f:
        raw_questions = json.load(f)

    QUESTIONS = defaultdict(list)
    for q in raw_questions:
        QUESTIONS[q["level"]].append(q)

    LEVELS = ["B1", "B2", "C1", "C2"]

    def level_up(cur):
        idx = LEVELS.index(cur)
        return LEVELS[min(idx + 1, len(LEVELS) - 1)]

    def level_down(cur):
        idx = LEVELS.index(cur)
        return LEVELS[max(idx - 1, 0)]

    # ————————————— Initialize State ———————————————————
    def init_state():
        st.session_state.score = 0
        st.session_state.level = "B1"
        st.session_state.qcount = 0
        st.session_state.maxq = 20
        st.session_state.stage = 'ask'
        st.session_state.current_q = None
        st.session_state.start_time = None
        st.session_state.help_time = None
        st.session_state.choice = None
        st.session_state.confidence = None
        st.session_state.log = []

    if 'score' not in st.session_state:
        init_state()

    # ————————————— Question Selection ——————————————————
    def pick_question():
        return random.choice(QUESTIONS[st.session_state.level])

    def load_next_question():
        st.session_state.current_q = pick_question()
        st.session_state.start_time = time.time()
        st.session_state.stage = 'ask'
        st.session_state.help_time = None
        st.session_state.choice = None
        st.session_state.confidence = None

    # ————————————— App Layout —————————————————————
    st.title("Adaptive English MCQ Test")
    st.write(f"Question {st.session_state.qcount+1} of {st.session_state.maxq}")
    st.write(f"Score: **{st.session_state.score}**")

    if st.session_state.current_q is None:
        load_next_question()

    q = st.session_state.current_q
    elapsed = time.time() - st.session_state.start_time

    # ————————————— Timer & Progress Bar —————————————————
    remaining = max(0, 180 - elapsed)
    progress_pct = min(elapsed / 180, 1.0)
    mins, secs = divmod(int(remaining), 60)
    progress_text = f"Time Left: {mins:02d}:{secs:02d}"
    my_bar = st.progress(int(progress_pct * 100), text=progress_text)

    if elapsed >= 178 and st.session_state.stage == 'ask':
        st.warning("⏳ 2:58 reached — automatically offering help")
        st.session_state.stage = 'help'
        st.session_state.help_time = time.time()

    # ————————————— Stage: ASK —————————————————————
    if st.session_state.stage == 'ask':
        st.write(q["question"])
        ans1 = st.radio("Your answer:", q["options"], key=f"ans1_{st.session_state.qcount}")
        conf = st.radio(
            "How confident are you?",
            ["High", "Medium", "Low"],
            key=f"conf_{st.session_state.qcount}"
        )
        if st.button("Submit"):
            st.session_state.answer_time = elapsed
            st.session_state.initial_answer = ans1
            st.session_state.confidence = conf
            correct = (ans1 == q["answer"])
            if elapsed <= 120 and correct:
                st.success("✅ Correct! +5 points")
                st.session_state.score += 5
                st.session_state.level = level_up(st.session_state.level)
                st.session_state.stage = 'final'
            else:
                st.warning("❌ Wrong or time >2min — offering help")
                st.session_state.stage = 'help'
                st.session_state.help_time = time.time()

    # ————————————— Stage: HELP —————————————————————
    elif st.session_state.stage == 'help':
        st.write("⏳ Choose one: 🧠 Hint, 📘 Example")

        c1, c2 = st.columns(2)
        with c1:
            if st.button("🧠 Hint"):
                st.session_state.choice = 'hint'
        with c2:
            if st.button("📘 Example"):
                st.session_state.choice = 'example'

        if st.session_state.choice:
            choice = st.session_state.choice
            help_elapsed = time.time() - st.session_state.help_time
            st.write(q["question"])
            if help_elapsed <= 60:
                if choice == 'hint':
                    st.info(f"Hint: {q['hint']}")
                    st.session_state.hint_binary = 1
                    st.session_state.example_binary = 0
                else:
                    st.info(f"Example: {q['example']}")
                    st.session_state.hint_binary = 0
                    st.session_state.example_binary = 1

                ans2 = st.radio("Your answer now:", q["options"], key=f"ans2_{st.session_state.qcount}")
                if st.button("Submit Second Answer"):
                    st.session_state.second_answer_time = help_elapsed
                    st.session_state.final_answer = ans2
                    correct2 = (ans2 == q["answer"])
                    if choice == 'hint':
                        if correct2:
                            st.success("✅ Correct with hint! +3")
                            st.session_state.score += 3
                            st.session_state.level = level_up(st.session_state.level)
                        else:
                            st.error("❌ Wrong with hint. -2")
                            st.session_state.score -= 2
                            st.session_state.level = level_down(st.session_state.level)
                    else:
                        if correct2:
                            st.success("✅ Correct with example! +2")
                            st.session_state.score += 2
                        else:
                            st.error("❌ Wrong with example. -2")
                            st.session_state.score -= 2
                            st.session_state.level = level_down(st.session_state.level)
                    st.session_state.stage = 'final'
            else:
                st.error("⌛ Help time expired. -2 points")
                st.session_state.score -= 2
                st.session_state.level = level_down(st.session_state.level)
                st.session_state.stage = 'final'

    # ————————————— Stage: FINAL —————————————————————
    elif st.session_state.stage == 'final':
        st.session_state.log.append({
            "question": q["question"],
            "initial_answer": st.session_state.initial_answer,
            "confidence": st.session_state.confidence,
            "initial_time": round(st.session_state.answer_time, 2),
            "hint_binary": st.session_state.hint_binary if 'hint_binary' in st.session_state else 0,
            "example_binary": st.session_state.example_binary if 'example_binary' in st.session_state else 0,
            "second_answer": st.session_state.final_answer if 'final_answer' in st.session_state else None,
            "second_time": round(st.session_state.second_answer_time, 2) if 'second_answer_time' in st.session_state else None,
            "score_after": st.session_state.score,
            "level_after": st.session_state.level
        })
        st.session_state.qcount += 1
        st.session_state.current_q = None

        if st.session_state.qcount >= st.session_state.maxq:
            df = pd.DataFrame(st.session_state.log)
            df.to_excel("results.xlsx", index=False)
            st.balloons()
            st.success("🎉 Test Complete!")
            st.write(f"**Final Score:** {st.session_state.score}")
            st.write(f"**Final Level:** {st.session_state.level}")
            with open("results.xlsx", "rb") as f:
                st.download_button(
                    "Download results as Excel",
                    f,
                    "results.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            st.stop()
        else:
            if st.button("Next Question"):
                load_next_question()




# ---- Column 2: Webcam Recording ----
with col2:
    user_name = st.text_input("Enter your name:", key="video_name")

    if user_name:
        sanitized_name = user_name.replace(" ", "_").lower()
        save_dir = os.path.join("recordings", sanitized_name)
        os.makedirs(save_dir, exist_ok=True)

        class VideoRecorder(VideoProcessorBase):
            def __init__(self):
                self.frames = []
                self.out = None
                self.output_filename = None

            def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
                img = frame.to_ndarray(format="bgr24")
                self.frames.append(img)

                if self.out is None and len(self.frames) == 1:
                    height, width, _ = img.shape
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    self.output_filename = os.path.join(
                        save_dir, f"recorded_{sanitized_name}_{timestamp}.avi"
                    )
                    self.out = cv2.VideoWriter(
                        self.output_filename,
                        cv2.VideoWriter_fourcc(*'XVID'),
                        20,
                        (width, height)
                    )

                if self.out:
                    self.out.write(img)

                return av.VideoFrame.from_ndarray(img, format="bgr24")

            def __del__(self):
                if self.out:
                    self.out.release()
                    print(f"✅ Saved at: {self.output_filename}")

        ctx = webrtc_streamer(
            key="auto_record",
            video_processor_factory=VideoRecorder,
            async_processing=True,
            media_stream_constraints={"video": True, "audio": False},
            rtc_configuration={
            "iceServers": [
            {"urls": ["stun:stun.l.google.com:19302"]},  # Free Google STUN
            # Optional: Add TURN server if needed
            # {"urls": ["turn:your.turn.server:3478"], "username": "user", "credential": "pass"}
        ]
        }
        )

        st.info("Recording automatically. Stop the stream to finalize.")
    else:
        st.warning("Please enter your name to start recording.")
