try:
    from pyi_splash import close
except ImportError:
    pass
else:
    close()

import shellsy.__main__

shellsy.__main__.main()
