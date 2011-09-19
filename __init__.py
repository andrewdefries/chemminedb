# import markdown first to allow it initialize its logger and set level
import markdown
# now reset the level to CRITICAL to mute it
from logging import getLogger, CRITICAL
logger = getLogger('MARKDOWN')
logger.setLevel(CRITICAL)
