import nonebot
from nonebot.adapters.onebot.v11 import Adapter as ONEBOT_V11Adapter

nonebot.init()

driver = nonebot.get_driver()
driver.register_adapter(ONEBOT_V11Adapter)


nonebot.load_from_toml("pyproject.toml")


def main():
    nonebot.run(host="0.0.0.0", port=8001)


if __name__ == "__main__":
    main()
