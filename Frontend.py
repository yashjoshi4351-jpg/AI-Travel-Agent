from Database import get_history, delete_history, clear_history
import streamlit as st
from ai_travel_agent import travel_agent   # your backend agent


# Page Configuration

st.set_page_config(
    page_title="AI Travel Concierge",
    page_icon="✈️",
    layout="wide"
)


# Session State for History

if "history" not in st.session_state:
    st.session_state.history = []


# Layout (Sidebar + Main)

# Chat
st.sidebar.title("Chat")

history = get_history()

if len(history) == 0:
    st.sidebar.write("No searches yet")

else:
    for item in history:

        query = item["query"]
        history_id = item["_id"]

        col1, col2 = st.sidebar.columns([4,1])

        # Click history
        if col1.button(query[:40] + "...", key=str(history_id)):
            st.session_state.selected_history = item

        # Delete
        if col2.button("❌", key="delete"+str(history_id)):
            delete_history(history_id)
            st.rerun()

# Clear history
if st.sidebar.button("🗑 Clear History"):
    clear_history()
    st.rerun()



# Main UI

st.title("✈️ AI Travel Concierge Agent")
st.write("Plan flights and generate a smart itinerary instantly!")

st.divider()


default_text = ""

if "selected_history" in st.session_state:
    default_text = st.session_state.selected_history["query"]

# User Input
user_input = st.text_area(
    "📝 Enter your trip details(Example : Make a trip plan from Udaipur to Goa from 2026-03-20 to 2026-03-30)",
    value=default_text,
    height=150
)
if "selected_history" in st.session_state:

    item = st.session_state.selected_history

    st.success("Loaded from history")

    st.subheader("📍 Trip Details")
    st.write(f"**Origin:** {item.get('origin')}")
    st.write(f"**Destination:** {item.get('destination')}")
    st.write(f"**Start Date:** {item.get('start_date')}")
    st.write(f"**End Date:** {item.get('end_date')}")
    st.write(f"**Travelers:** {item.get('travelers')}")

    st.divider()

    st.subheader("🗺️ Travel Itinerary")
    st.markdown(item.get("itinerary"))


# Plan Trip Button


if st.button("🚀 Plan My Trip"):

    if user_input.strip() == "":
        st.warning("Please enter your travel details.")

    else:
        with st.spinner("Planning your perfect trip... ✨"):

            try:
                result = travel_agent(user_input)

                if result.get("error"):
                    st.error(f"❌ {result['error']}")

                else:
                    st.success("✅ Trip Planned Successfully!")


                    # Trip details
                    st.subheader("📍 Trip Details")
                    st.write(f"**Origin:** {result.get('origin')}")
                    st.write(f"**Destination:** {result.get('destination')}")
                    st.write(f"**Start Date:** {result.get('start_date')}")
                    st.write(f"**End Date:** {result.get('end_date')}")
                    st.write(f"**Travelers:** {result.get('travelers')}")

                    st.divider()

                    # Itinerary
                    st.subheader("🗺️ Your Travel Itinerary")
                    st.markdown(result.get("itinerary"))

            except Exception as e:
                st.error(f"Something went wrong: {str(e)}")