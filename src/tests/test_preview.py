from shellsy.interpreter import S_Interpreter as Interp


def test_preview():

    """ """
    inter = Interp()




    assert inter.eval("echo 3") == 3
    assert inter.eval("echo '3'") == '3'

    inter.eval("echo /3/")

    inter.eval("echo 3.3")
