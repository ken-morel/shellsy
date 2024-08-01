from shellsy import __main__
try:
    import pyi_splash
    pyi_splash.close()
except ImportError:
    pass


__main__.main()
