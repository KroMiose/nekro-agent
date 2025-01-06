try:
    import nonebot
    from nonebot.adapters.onebot.v11 import Adapter as ONEBOT_V11Adapter

    nonebot.init()

    driver = nonebot.get_driver()
    driver.register_adapter(ONEBOT_V11Adapter)

    nonebot.load_from_toml("pyproject.toml")
except Exception as e:
    import traceback

    traceback.print_exc()
    print(f"Nonebot Init Error: {e}")
    raise


def main():
    try:
        nonebot.run(host="0.0.0.0", port=8021)
    except Exception as e:
        import traceback

        traceback.print_exc()
        print(f"Plugin Load Test Error: {e}")
        raise


if __name__ == "__main__":
    main()
