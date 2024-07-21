import datetime, os

from djamago import *


class Main(Topic):
    @Callback(r"-question(asking_time)")
    def give_time(node):
        return Response(
            datetime.datetime.now().strftime(
                "The current time is %h %m"
            ),
        )

    @Callback(r"start@app('.*subl.*')")
    def start_app_subl(node):
        def gen():
            yield "launching sublime with subl..."
            os.system("subl")
            yield "sublime launched!, can code now!"
        return SyncResponse(gen())
