from djamago import Expression


Expression.register("Any", [(100, ".*")])

Expression.alias("question", "-question")
Expression.extend("question", [
    (100, r"(.+),? please\??"),
])

Expression.register("asking_time", [
    (100, r"what (?:time is it|is the time)?\??"),
    (100, r"(?:give me ?)?(?:the ?)?time\??"),
    (100, r"what time.*\??.*"),
])

Expression.register("start@app", [
    (100, r"(?:start|run|open) app (.+)"),
    (40, r"(?:open|launch) (.+)"),
])
