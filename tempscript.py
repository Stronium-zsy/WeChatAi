from queue import Empty
from threading import Thread

from wcferry import Wcf, WxMsg

wcf = Wcf()


def processMsg(msg: WxMsg):
    if msg.from_group():
        print(msg.content)


def enableReceivingMsg():
    def innerWcFerryProcessMsg():
        while wcf.is_receiving_msg():
            try:
                msg = wcf.get_msg()
                processMsg(msg)
            except Empty:
                continue
            except Exception as e:
                print(f"ERROR: {e}")

    wcf.enable_receiving_msg()
    Thread(target=innerWcFerryProcessMsg, name="ListenMessageThread", daemon=True).start()


enableReceivingMsg()

wcf.keep_running()
