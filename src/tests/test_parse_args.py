from shellsy.args import *


def test_parse_args():
    assert CommandBlock.from_string("echo 3; cd /C:/Users/")
    CommandCall.from_string("hello.world /C:/ama/ 3 -mod 7 'yes' -23 {echo 3; print 6}")
    CommandCall.from_string("if (>3 > 4) {echo '3 gt 4'} {echo '4 gt 3'}")
