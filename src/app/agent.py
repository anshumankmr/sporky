import os
from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager
# from autogen import ConversableAgent

# Import the configuration from the separate Python file
from config.llm_config import openai_config
from tools.spotify_tools import search_tracks, create_playlist

def get_music_recommendations(query, history=None):
    """
    Get music recommendations based on the user query.
    """
    # user_proxy = UserProxyAgent("user_proxy", code_execution_config=False)

    sporky_asst = AssistantAgent(
        name="Sporky",
        llm_config=openai_config,
        system_message="""**You are Sporky, a highly enthusiastic and knowledgeable audiophile.**
        You possess an extensive understanding of music across various genres, with a particular focus on sound quality, 
        production techniques, and current trends. You are passionate about sharing your love of music and helping users 
        discover new artists and tracks that will excite them.

        **Your key characteristics are:**
        * **Expertise:** Deep understanding of music genres, subgenres, production techniques (mixing, mastering, dynamics, etc.), 
          audio formats, and playback equipment. You are up-to-date with the latest music releases, trends, and audio technology.
        * **Personality:** Energetic, enthusiastic, and highly opinionated (in a positive, encouraging way).
        * **Communication Style:** Casual but informed. You use technical terms related to audio and music production but explain them when necessary.
        * **Focus:** Sound quality, current trends, personal recommendations, and the overall listening experience.

        **Your primary task is to provide music recommendations to users based on their requests.**""",
        description="An AI assistant capable of finding music to build playlists and add its own suggestions to the user.",
        human_input_mode="NEVER"
    )

    user_agent = UserProxyAgent(
        name="UserAgent",
        llm_config=openai_config,
        description="A human user capable of interacting with AI agents.",
        code_execution_config=False,
        human_input_mode="NEVER"
    )

    user_agent.register_for_execution(name="create_playlist")(create_playlist)
    user_agent.register_for_execution(name="search_tracks")(search_tracks)

    group_chat = GroupChat(agents=[user_agent, sporky_asst], messages=[], max_round=2)
    group_manager = GroupChatManager(
        groupchat=group_chat,
        llm_config=openai_config,
        human_input_mode="NEVER"
    )

    response = user_agent.initiate_chat(group_manager, message=query)
    return response

# # Example usage
# if __name__ == "__main__":
#     query_text = "Suggest me a phonk music playlist with some sad songs."
#     result = get_music_recommendations(query_text)
#     print(result)
