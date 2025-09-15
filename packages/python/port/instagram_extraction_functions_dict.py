import port.instagram_extraction_functions as ef

# defines which extraction functions are used and what titles are displayed
# patterns are names of files or paths to that file if filename in path (like in personal_information/personal_information)

extraction_dict = {
    "time_spent": {
        "extraction_function": ef.extract_time_spent,
        "patterns": [
            "posts_viewed",
            "videos_watched",
        ],  # This function requires both files
        "title": {
            "en": "How much time did you spend on Instagram? [seconds per day]",
            "de": "Wie viel Zeit haben Sie auf Instagram verbracht? [Sekunden pro Tag]",
            "nl": "Hoeveel tijd heeft u op Instagram doorgebracht? [seconden per dag]",
        },
    },
    "ads_seen": {
        "extraction_function": ef.extract_ads_seen,
        "patterns": ["ads_viewed"],
        "title": {
            "en": "How often did you see ads? [per day]",
            "de": "Wie oft haben Sie Werbung gesehen? [pro Tag]",
            "nl": "Hoe vaak heeft u advertenties gezien? [per dag]",
        },
    },
    "ads_clicked": {
        "extraction_function": ef.extract_ads_clicked,
        "patterns": ["ads_clicked"],
        "title": {
            "en": "On how many ads did you click? [per day]",
            "de": "Wie oft haben Sie Werbung angeklickt? [pro Tag]",
            "nl": "Hoe vaak heeft u advertenties aangeklikt? [per dag]",
        },
    },
    "recently_viewed_items": {
        "extraction_function": ef.extract_recently_viewed_items,
        "patterns": ["recently_viewed_items"],
        "title": {
            "en": "Which shopping items have you recently viewed?",
            "de": "Welche Einkaufsartikel haben Sie sich kürzlich angesehen?",
            "nl": "Welke winkelartikelen heeft u onlangs bekeken?",
        },
    },
    "combined_views": {
        "extraction_function": ef.extract_combined_views,
        "patterns": ["posts_viewed", "videos_watched"],
        "title": {
            "en": "How many posts and videos have you seen? [per day]",
            "de": "Wie viele Posts und Videos haben Sie gesehen? [pro Tag]",
            "nl": "Hoeveel posts en video's heeft u bekeken? [per dag]",
        },
    },
    "combined_blocks": {
        "extraction_function": ef.extract_combined_blocks,
        "patterns": ["blocked_profiles", "restricted_profiles"],
        "title": {
            "en": "How often did you block or restrict other profiles? [per day]",
            "de": "Wie oft haben Sie andere Profile blockiert und eingeschränkt? [pro Tag]",
            "nl": "Hoe vaak heeft u andere profielen geblokkeerd en beperkt? [per dag]",
        },
    },
    "combined_comments": {
        "extraction_function": ef.extract_combined_comments,
        "patterns": ["post_comments_1", "reels_comments"],
        "title": {
            "en": "How often have you commented on posts and reels? [per day]",
            "de": "Wie oft haben Sie Posts und Reels kommentiert? [pro Tag]",
            "nl": "Hoe vaak heeft u posts en reels becommentarieerd? [per dag]",
        },
    },
    "combined_likes": {
        "extraction_function": ef.extract_combined_likes,
        "patterns": ["liked_posts", "story_likes", "liked_comments"],
        "title": {
            "en": "How often have you liked posts, stories or comments? [per day]",
            "de": "Wie oft haben Sie Posts, Stories oder Kommentare geliked? [pro Tag]",
            "nl": "Hoe vaak heeft u posts, stories of commentaren geliked? [per dag]",
        },
    },
    "combined_story_interactions": {
        "extraction_function": ef.extract_combined_story_interactions,
        "patterns": ["countdowns", "emoji_sliders", "polls", "questions", "quizzes"],
        "title": {
            "en": "How often did you interact with Stories? [per day]",
            "de": "Wie oft haben Sie mit Stories interagiert? [pro Tag]",
            "nl": "Hoe vaak heeft u met Stories geïnteracteerd? [per dag]",
        },
    },
    "posts_created": {
        "extraction_function": ef.extract_posts_created,
        "patterns": ["posts_1"],
        "title": {
            "en": "How often have you published posts and did you add location information? [per day]",
            "de": "Wie oft haben Sie Posts veröffentlicht und hatten Sie Standortinformationen hinzugefügt? [pro Tag]",
            "nl": "Hoe vaak heeft u posts gepubliceerd en heeft u locatie-informatie toegevoegd? [per dag]",
        },
    },
    "stories_created": {
        "extraction_function": ef.extract_stories_created,
        "patterns": ["stories"],
        "title": {
            "en": "How often have you published stories and have you added location information? [per day]",
            "de": "Wie oft haben Sie Stories veröffentlicht und haben Sie Standortinformationen hinzugefügt? [pro Tag]",
            "nl": "Hoe vaak heeft u stories gepubliceerd en heeft u locatie-informatie toegevoegd? [per dag]",
        },
    },
    "reels_created": {
        "extraction_function": ef.extract_reels_created,
        "patterns": ["media/reels"],
        "title": {
          "en": "How often have you published reels and have you added location information? [per day]",
          "de": "Wie oft haben Sie Reels veröffentlicht und haben Sie Standortinformationen hinzugefügt? [pro Tag]",
          "nl": "Hoe vaak heeft u reels gepubliceerd en heeft u locatie-informatie toegevoegd? [per dag]",
        },
    },
    "followers_new": {
        "extraction_function": ef.extract_followers_new,
        "patterns": ["followers_1"],
        "title": {
            "en": "How often do you have new followers? [per day]",
            "de": "Wie oft haben Sie neue Follower? [pro Tag]",
            "nl": "Hoe vaak heeft u nieuwe volgers? [per dag]",
        },
    },
    "search_history": {
        "extraction_function": ef.extract_search_history,
        "patterns": ["word_or_phrase_searches"],
        "title": {
            "en": "How often have you searched on Instagram? [per day]",
            "de": "Wie oft haben Sie nach etwas gesucht? [pro Tag]",
            "nl": "Hoe vaak heeft u naar iets gezocht? [per dag]",
        },
    },
    "messages": {
        "extraction_function": ef.extract_messages,
        "patterns": ["message_1.json"],
        "title": {
            "en": "How often have you sent messages on Instagram? [per day]",
            "de": "Wie oft haben Sie Nachrichten auf Instagram geschrieben? [pro Tag]",
            "nl": "Hoe vaak heeft u berichten op Instagram geschreven? [per dag]",
        },
    },
    "contact_syncing": {
        "extraction_function": ef.extract_contact_syncing,
        "patterns": ["instagram_profile_information"],
        "title": {
            "en": "Have you enabled contact syncing?",
            "de": "Haben Sie die Kontaktsynchronisierung aktiviert?",
            "nl": "Heeft u de contactsynchronisatie geactiveerd?",
        },
    },
    "private_account": {
        "extraction_function": ef.extract_private_account,
        "patterns": ["personal_information/personal_information.json"],
        "title": {
            "en": "Do you have a private (not public) account on Instagram?",
            "de": "Haben Sie ein privates (nicht öffentliches) Konto auf Instagram?",
            "nl": "Heeft u een privé (niet openbaar) account op Instagram?",
        },
    },
    "topic_interests": {
        "extraction_function": ef.extract_topic_interests,
        "patterns": ["your_topics"],
        "title": {
            "en": "What interests has Instagram inferred about you?",
            "de": "Welche Interessen hat Instagram über Sie abgeleitet?",
            "nl": "Welke interesses heeft Instagram over u afgeleid?",
        },
    },
    "login_activity": {
        "extraction_function": ef.extract_login_activity,
        "patterns": ["login_activity"],
        "title": {
            "en": "When and with which device/browser did you log in to Instagram?",
            "de": "Wann und mit welchem Gerät/Browser haben Sie sich bei Instagram angemeldet?",
            "nl": "Wanneer en met welk apparaat/browser heeft u zich bij Instagram aangemeld?",
        },
    },
    "logout_activity": {
        "extraction_function": ef.extract_logout_activity,
        "patterns": ["logout_activity"],
        "title": {
            "en": "When and with which device/browser did you log out of Instagram?",
            "de": "Wann und mit welchem Gerät/Browser haben Sie sich bei Instagram abgemeldet?",
            "nl": "Wanneer en met welk apparaat/browser heeft u zich bij Instagram afgemeld?",
        },
    },
}
