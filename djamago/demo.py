try:
    from . import *
except ImportError:
    from __init__ import *

import random
import datetime


Expression.register(
    "greetings(-greetings)",  # Subclass the predefined -greetings
    [
        (100, r"haloa!?"),
    ],
)

Expression.alias("greetings_to", "-greetings-to")

Expression.register(
    "aking_current-time",
    [
        (100, r"what time is it(?:\s*now)?"),
        (100, r"que es la hora"),
        (70, r"time please"),
    ],
)

Expression.register(
    "aking_current-date",
    [
        (100, r"what day (?:are|is) (?:it|we)(?:\s*(?:now|today))?"),
        (100, r"what the date of today"),
        (70, r"date please"),
    ],
)


class Chatbot(Djamago):
    def __init__(self):
        super().__init__("John Doe", topics="main")


@Chatbot.topic
class Main(Topic):
    @Callback(r"greetings")  # matches greetings
    def greet(node):
        node.response = "Hy"

    hy_from = Callback(r"greetings_to('.+'#collected_name)")(
        responses=["Hy! (from %(collected_name)s)"],
    )  # and store match as colletced_name

    @Callback(r"'.*how are you.*'")
    def how_are_you(node, cache={}):
        if "asked" not in cache:
            node.response = Response(
                "I am a bot. you know I cannot feel bad. Nor fine too :cry: "
                "but I will say I feel fine, and you?"
            )
            cache["asked"] = True
            node.set_topics("howareyou")
        else:
            node.response = Response(random.choice(
                (
                    "I do not know, you tell me, How am I?",
                    "you again and that question!",
                    "why not doing something completely different now?",
                    "Cameroon government calls, `CHANGE TOPIC`",
                )
            ))

    @Callback(r"-question(aking_current-time)")
    def current_time(node):
        print(node.score)
        node.response = Response(datetime.datetime.now().strftime(
            random.choice((
                "We are a %A and it is: %I:%M",
                "It is: %I:%M",
            )),
        ))

    @Callback(r"-question(aking_current-date)")
    def current_date(node):
        node.response = Response(datetime.datetime.now().strftime(
            random.choice((
                "We are a %A on the %d of %B",
            )),
        ))


@Chatbot.topic
class HowAreYou(Topic):
    feel_fine = Callback(r"'.*(?:fine|well|ok|nice|I am).*'")(
        responses=["feel fine!, that is good!, Well letá change topic"],
        topics=("main",)
    )
    fallback = Callback(r"'.*'")(
        responses=["that is not what I expected as answer..."],
        topics=("howareyou",)
    )


bot = Chatbot()


def cli():
    msg = ""
    while msg != "quit":
        print(bot.respond(msg := input("> ")).response)


if __name__ == '__main__':
    cli()
