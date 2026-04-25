from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "mem_episode" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "workspace_id" INT NOT NULL,
    "origin_chat_key" VARCHAR(128),
    "title" VARCHAR(256) NOT NULL,
    "narrative_summary" TEXT NOT NULL,
    "time_start" TIMESTAMPTZ,
    "time_end" TIMESTAMPTZ,
    "participant_entity_ids" JSONB NOT NULL,
    "paragraph_ids" JSONB NOT NULL,
    "phase_mapping" JSONB NOT NULL,
    "base_weight" DOUBLE PRECISION NOT NULL DEFAULT 1,
    "is_inactive" BOOL NOT NULL DEFAULT False,
    "embedding_ref" VARCHAR(64),
    "create_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "update_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS "idx_mem_episode_workspa_26f360" ON "mem_episode" ("workspace_id");
CREATE INDEX IF NOT EXISTS "idx_mem_episode_origin__f191e8" ON "mem_episode" ("origin_chat_key");
CREATE INDEX IF NOT EXISTS "idx_mem_episode_time_st_5986c3" ON "mem_episode" ("time_start");
CREATE INDEX IF NOT EXISTS "idx_mem_episode_time_en_7a573f" ON "mem_episode" ("time_end");
CREATE INDEX IF NOT EXISTS "idx_mem_episode_is_inac_98d674" ON "mem_episode" ("is_inactive");
CREATE INDEX IF NOT EXISTS "idx_mem_episode_embeddi_a463a0" ON "mem_episode" ("embedding_ref");
CREATE INDEX IF NOT EXISTS "idx_mem_episode_workspa_7cbd29" ON "mem_episode" ("workspace_id", "origin_chat_key");
CREATE INDEX IF NOT EXISTS "idx_mem_episode_workspa_cddfbb" ON "mem_episode" ("workspace_id", "time_start");
CREATE INDEX IF NOT EXISTS "idx_mem_episode_workspa_93a4d3" ON "mem_episode" ("workspace_id", "time_end");
CREATE INDEX IF NOT EXISTS "idx_mem_episode_workspa_dafd46" ON "mem_episode" ("workspace_id", "is_inactive");
COMMENT ON COLUMN "mem_episode"."id" IS '主键 ID';
COMMENT ON COLUMN "mem_episode"."workspace_id" IS '工作区 ID';
COMMENT ON COLUMN "mem_episode"."origin_chat_key" IS 'Episode 来源聊天频道';
COMMENT ON COLUMN "mem_episode"."title" IS 'Episode 标题';
COMMENT ON COLUMN "mem_episode"."narrative_summary" IS 'Episode 叙事摘要';
COMMENT ON COLUMN "mem_episode"."time_start" IS 'Episode 起始时间';
COMMENT ON COLUMN "mem_episode"."time_end" IS 'Episode 结束时间';
COMMENT ON COLUMN "mem_episode"."participant_entity_ids" IS '参与实体 ID 列表';
COMMENT ON COLUMN "mem_episode"."paragraph_ids" IS '包含的段落 ID 列表';
COMMENT ON COLUMN "mem_episode"."phase_mapping" IS '阶段到段落 ID 的映射';
COMMENT ON COLUMN "mem_episode"."base_weight" IS 'Episode 基础权重';
COMMENT ON COLUMN "mem_episode"."is_inactive" IS '是否已失活';
COMMENT ON COLUMN "mem_episode"."embedding_ref" IS '预留向量引用';
COMMENT ON COLUMN "mem_episode"."create_time" IS '创建时间';
COMMENT ON COLUMN "mem_episode"."update_time" IS '更新时间';
COMMENT ON TABLE "mem_episode" IS 'Episode 聚合记忆模型。';
        ALTER TABLE "mem_paragraph" ADD "episode_id" INT;
        ALTER TABLE "mem_paragraph" ADD "episode_phase" VARCHAR(16);
        COMMENT ON COLUMN "mem_paragraph"."episode_id" IS '所属 Episode ID';
COMMENT ON COLUMN "mem_paragraph"."episode_phase" IS '在 Episode 中的阶段';
        CREATE INDEX IF NOT EXISTS "idx_mem_paragra_episode_8f0c86" ON "mem_paragraph" ("episode_id");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "idx_mem_paragra_episode_8f0c86";
        ALTER TABLE "mem_paragraph" DROP COLUMN "episode_id";
        ALTER TABLE "mem_paragraph" DROP COLUMN "episode_phase";
        DROP TABLE IF EXISTS "mem_episode";"""


MODELS_STATE = (
    "eJztXXlz28iV/yos/jWp0oxB3JjaSpUsOxtv+ZjY8iabOMVqAA0KMQkwAOgjM/Pdt183jg"
    "bQIAmIJFoSKhWPRPRrQr/Xx7vfr/NN7ON1+tOL5zd3KCP/jyK8nv88+3UeoQ0mP4gHXM3m"
    "aLutHsMHGXLXlMIjA5ceN9JNswR5GXkWoHWKyUc+Tr0k3GZhHAHFp51pWAr5VzPxp52BHe"
    "3TzlZ0RH52VOfTzrGdBflXMcjnJlLJz4ZluzC3H3tk8jBa3W+aXRT+e4eXWbzC2R1OyGT/"
    "+Cf5OIx8/A2nxa/bz8sgxGu/hk/owwT082X2fUs/exVlf6ID4Q3dpRevd5uoGrz9nt3FUT"
    "k6jDL4dIUjnKAMw/RZsgOYot16naNaIMfetBrCXpGj8XGAdmsAG6jbWL960cQtH+fFEfCJ"
    "vE1K/8AVfMuP6kK3dFszdZsMoW9SfmL9zv686m9nhPRb3t7Of6fPUYbYCAojh1u6JGsi/I"
    "Lb8D2P4zVGUQeEPF0DSZcQNqEsgNuHZfFBBWa1UAs0S3ibK9dUA7KQdNUkPwceLD9fa61N"
    "McZ7AHz+7t1rmGSTpv9e0w9e3cLvMdlJbJu9/fjm+cv3Pyz+AB+TQWGGeeQrpLcJTnG27L"
    "VQazSH16sA5ByvXhiLV+ynnY5dsolt18Wzyy7fCkRYx238bvG3DgCL8Q3syCuea4F2gVc7"
    "9crz8d4L9Pbl325rC/Tt/16/v/nz9fsf3lz/ja7Jzff8yet3b/+7GM6t35vX7543UEY+2m"
    "Y4WX7G39tgk8snEYPdIDsX5keesAC2opJ/F7pPTgbTtAnktmLBCvbMI5fvBn1brnG0yu7I"
    "r6a+hxEF7Kb+hwbA+ROVPqoDnV/PwkOhG+c61fgwlyv7+GPhQrjS3wcgW9ANwvaURy5/ah"
    "i6Qhay5QSKXCBTdAaAXNBJBbLlWa5Yrj0GZE09AmRN7QQZHrVAzvqewzzN6KeDsYCD1/B0"
    "pVsLMAwQ3nSsKBIe0XH0BScpgr9omWYoyZZZKDpVXhA84UkHT7qnabDIz+f5qfjh0pKK4Q"
    "YOcMAnp43tWxZwzHNBagmIcO0YgX4kZxKM/HfR+nu+XPZJMa/evPxwe/3ml5oo8+L69iU8"
    "UWtiTPHpD2aDi+Uks7++uv3zDH6d/f3d25cU4zjNVgn9xmrc7d/n8E5ol8XLKP66RD63so"
    "tPC+hqi+JrnHxOt8jD/cT5JtnoEr2xsKhybujkZx8bZBMGhkd+1jQ0mozvkXWT4WG7rE4q"
    "3c5SF3C5kHHTbuIYvtv6QxneIJWN4aYZ6MBqV3nCDKcvD4a74DNngoIPXOR9/ooSf9l6Eq"
    "tx19j2o426aX6CIrSivAJs4S1r9tM3OE0RPbU6DKzFgKuDBtYNN/LeBlbTt0FJVczgXgbW"
    "7mkmA+vFDawpJm+e9NTwa0Tji/CaT0V1ZQHrTDEGqvkL1T5COCejOqVz+qwuLORI9VX0G2"
    "TSQUwUUWsBBm3XwXCNaMZwzf+suIfe56HYc6QS4k8wx4C5hqTEP0zJKS7CvftMrigG6R0n"
    "Fowqdw3R+/HseZzNCMRmYDOtZBzVg2CUYA+t11hwXB/yh/GUF/SIHQcxXcY6Aj3P9DEvI8"
    "jkI5scDxeyauVia0+xpE41Osy8nGtgsGQYWqDI5IR42KbbB2muBQAHeCQqImlhl801sV2j"
    "LIiTzXKX4qTfQSIgHR326gQhUBsqnCyqZg08TVTDPAJuMqoTb/qs5YrIcERWKv6WtdHuDo"
    "Jo0o0fDFE7uRe2AYqOC5YLwyaniWmp3r2lkrMERhRI9g1DadLJzIHCsjT7nw/v3srJhgR9"
    "XXr/Jvj6gmO+mwsNsvGZYGhOwLxrs5u/gPpjKws5ESeY9l70PM34WJuq6YAf2jDkj78CCw"
    "n1aaQZ2mx76PhtwnOp+oMsK5ULhF6uIyn5k3/xUbubJv/iE2O4XP7Fl9+wdwMShtC5WD69"
    "2udZJOvAK8WUYW5Fct2BXm7rHmjqWGPCRW+34nHTTG7Fi7sVJ+PSCMYl8u2rFU6o1aKn6V"
    "RAejEWzJnbqsUBB5uFfFYZPCSyd9Qw6+tlFBJfTg2Zf/ieZnjTA3gW4C2NgzHdeR5O055u"
    "MI7qgi6w7nuRzwpTFwqIyI5UHi+45QcY9DgiKVRrsZAguTUv3mXbXSZY4t3IcyTj424HIK"
    "IZC1D3LOyDuGY5kmJNjuEllXT7nOE1ooulicyFh7YeWEF5XHcK0aMd1wSb3eqOJnyHUZ8V"
    "3SIcPR3HVBaQ54RBtXX0AAP2eHGiYIXz2OuyeNvhdCS6zMtot6HYvyIviSIPt29Nnv5ywT"
    "mKCH1DgQQA0zXVAR5HpvRoqmWW+g78sk/V+fDm+vXr9r1IVWAwqSw3ggO6U0Nsko0MJn8z"
    "VvaZHwBf7EJEmc8crpc3guYQQDZSf5TFxCNjbRkQMMmkPLmwzuIMrQfA3KIb+2jQPZ8ahs"
    "DmqGguKPELi6EtA87kjkvQEDcVR3VBDVEoZji2Axg7C1N+N9XkSHnUdvXJkfLEGC6XI+UN"
    "3ryMsjD7Phd6UqrHV/tcKRu8WeJq3BG+FNuFRWAEnlmkX+jBwYpXh4k+ReR/RBSEaGA7cD"
    "FV2UtLN09jqzbI3gqE4wSB4hVap45t3Bjp0u9TVXJYadTDbgSGWs6pwSVi6LZXJPpaXgB5"
    "3JatF4cboVKP8+D8o5W97KEojkIP5eUyyPj2GAY92+f/fDROIBpQ78IZoV66FFK3R2jMnP"
    "STBoy089DpPiA7wDFB9LQc16V7yIGdAaoVeeqMJHJy67uFORi2Div/jSlGd8zxB8z9Qo4X"
    "x/iEFt0uoUXLI9TXCSRPfhkHalXHp1jXVRxgr7V8gYjj+hHfA/k25eg8sB2PnB62pmjV3d"
    "jkRO2m1eCccRZU6WW3aOt2lYpbaB2iFAssDBDJ25E5VZE0+PMxIsD9ww+97Gq2DtPsn2fT"
    "g/8r2EUesGnm7sJ1FkbpT/CFfxTqx0zYYYwjWppViFTAPvgzZ4XabGHg9vH82cOOIhC6W3"
    "lu6skNSRwmaNXY224xSuBGIOzYRQL/X+eVLSK9nGloIWQLc0JpVH9y1QXjwjh3chrvEgLN"
    "XSgC9bg7uTHFBY1CERJ7n6i8aTs2IGuZEMOMHWoc8pUiSxm2QISeef0EotqxdIxjqtstJU"
    "pSDqOh5WV5yrPFErQuj6NCCQw/UOG+1hYSlpktUqtCn0qWYb8LoYP8YVwOto/teiKXjZEL"
    "uyfwKQfh3vYUvdQnbNCELcOAzADXAFO26xoy3xqTyfVRW+Amk+sTY7h8JtdtmHZGr3PPrw"
    "4aXbmBB62u+awzWosQUfnerhtVOUNqabSs2WCHTTHE7hkn4SqMlmU0tdDwSb22tM7nnuc4"
    "8sVPefFnMpueQDt4kmbTcdSv5vYQqmAd0ZVt0jNFox0Ja3Wo8EqXOHVhkIX0LKGAYbbuFy"
    "pfEIwd0srBTTM/CLi2NNa1CCUQ8/SFHOu7zQYlgpXdHWQiJJYHbkPzHWr2BPegbtjM1HBv"
    "FegsUSfczdpTIK5TnkAePsM5c5+C2w9ECi5Q2qv3lPLREB7ndHJyuIjUN4KnzeEt2YehF2"
    "5RlOURGkSU6mer6pzhYZirDM1j7qRaWAcR3Ga8b0NOQxTBHq0StL0bwLQ64UPhFRQFNXTw"
    "PlkmmA2ZqdDWNf+BcOwOQToN0drhrfpwrEkoE8fga8Ucc0zNLLhkqJrS5ljOx9IsLCffXE"
    "D/Kw5XdwKB50/rGHWInA26BtMCIDwXoxY/CeLHOWnTos5CG1rCmJauMSf7vdF/8e7j89cv"
    "Z7+8f3nz6sOrnBPllUcf1p0n719ev548VqN7rPDGxb5P3mOZ4KCP3toiHNdY0PAn6YsFXd"
    "jAg2BhsNiSIdrsGYpkTl6kx+xUmLxIT4zh0nmR3mA/RO8xC6OZd/mS6qOuDnmUNjCcHPXc"
    "+L7h/MhRy9h5X9fLKJqjQ/sPTsDC/K1godGQApvmcqFihMkaDHCUuQxaVkooAgtNDS4OO8"
    "hDE71CQ2QhVkFA5owWP83qxTsN3aPxD3Q4F73IJnAUixb7hKrkeVSjo7B/4dbSFfNTpNIp"
    "y+uqSMAm7wHN4LCKyrcJIEGYZVtyCEEeJnYhUd5XVfJbpMGEtMI/sLBU/mafuN5jQx1xbE"
    "Gw3AKRF41IBTjBVZjc5EmbT560B+RJK6oGE/37ro9c3KQ7jZ9h+Frlzzv+uIKzb/bmhfHs"
    "w5+vVcOc1Q+wPDSeax/KlwYbGuF4jlYK5Skk5NHhaNP6DGN7heq3nGwZIPzLtuDe0we+Tj"
    "ZyjZPrV7N6vYK2FFDd/5J64dCql9m3GC+T7bDb2svcz5Zr4QeeZfB4bCuGhgNaR9optgtv"
    "YaHiZi64ymZtYVEtaE1mJN/SM49KSDx6iSY+YY2dWjoOzOEVDM8SsAGILdPwP32apNVoRm"
    "/PXIPWUS3qpghK0YhGrLNs8fEyYP1wg6OUvHKv66BOdYJL4aSr2wSd11J16xnNGjSLMC/D"
    "gzwbww3skgeOrc5+/Rr62d3PM1tRrmZ31ONCzhFF+V3mm8HfsQpOvXxKPNFAh9IpGeVYgV"
    "bnUGECtMpdAvWITsSHUziYNhCf0q0siGGvEY18+L8Bq+V99YLTX7JNW8/xR76AcuRkStuG"
    "pCXeCjd2SmUQJmm2TDGOlqh32F2LWDYfguM4ZoFxLZH1qfoT2g6kNRrO/yatbOw3LZrPr9"
    "MwrIn95cuLDtd13Ct0qEX4MNR//ugtnBuGsU/9B/eKadD64jTqiC4pO/AXs7cseWAhsyw4"
    "xQM86v08xQM8MYZLFw/wS+H3nXfFAlQjrg7FAWxrQ3uGAFQxoD3c/mIi5uo3VYsa6i2/sF"
    "GatqcUFsncUknTa5gznzfys4uDxenx38fq9LH6gLlrwNZs+rQKK1AQrRwF95KxgCDKe9Xy"
    "i1dRSPOTut3pBPs4+b7Mwy8O560K6wF+oY1o4WCYvPHzyRv/yMoB1rdIC/U9Fp4m4fjV0v"
    "jzj0t+la/KUOPsEqJ+2AnfnkUCFiBY3xZsgMrexljAyiuE3rMUk6s3C+/BjtM76T8TMWSN"
    "/dX9ONKeZXSOMF6wsruyRUbkUT9ttA+2JT8ntMdL7vyBw+7TvFwmFzGUm/RdlXaaUmjOso"
    "uKEo68mHUSZfs8zWK6sse7b4f75oyf0udiubZCN4LPp4oL62cG0A/CUSDMhfXdLuvUDTqn"
    "jIV6xJ4hozo3DX3WCJCoBNIWQ/YrwnVKmXKNi0z+3HGc9xlc1PKNKydy4MyKywT8OqrlFF"
    "U2WZBwyd4T7CeJtOajcpTzIkb9ROg60ZmCCI5eCqZKQyc9A8+KDLyx4lkLYGhC6VCpoDXJ"
    "6CeiYan2rMpu1LHqF2p7lYMqh4zwWHJJpc4hpf6uBIdREBNlzh/qMWvNcJErZpjbLG/XzD"
    "yoAQ2SYVksT7i+xR1aB8t1GOBlismfKaqS0HmFCGkvF5VgqYp402lQ+Mq2aVsqazE4xubU"
    "F8uUtT1lbQ+VkP7iJyjKZnw4cV7PQ8ow4uXnUFQU6TjZqTHF+Do/b1iUzZ6Sg9VzddepRp"
    "dNeYD5qAZ2bpu+bbO+uq9ePKP6InBARQuwsVuu7kjW4OIxlZZsGryQVSjpTHUQF5ksUlPA"
    "BDlom5yj4CQ5a+7iZLlJV0JFuZspLcKxWeIYCxrg7aDKdQuGKxbAU8t6KLfO8er0mS+IGp"
    "pdFRKPZEZnmcQR1Gs3AKuu6/ssJr90x/OVEmXnhrCS4bG8EJczlIcTtYqG0nICVGSyqjfb"
    "rq3R3W+nc4LRM4SO2hyc0ddUtWMLFZ9YR2uBKNwSx/NAvCnk4YC4zOeYHCC67jaJM+wBLi"
    "3kD6nJNdKz6clt3DsVZUPzITkuAOBNFZVxuKanURcUlDaxFxhRiRbOJAwVHKHMiUxqNEE2"
    "SOL/YEEe1iGOVHRSsGPhusWqt1TXLIrdFDFukKVoKBDFw+xHBlG0ZWLEBkU7tM6N3Esfr0"
    "Vd5PeYyDvoL2kqV8SmclPV3WIT2B50PzQNSy8jC0vjORljQ4kh5xScOZkhPccVeeJkxW4Z"
    "Skw9uhDVZTbnuWTqwA0W83Y/s4h2jMtc6/aYay2HeRvWoQ4O0SQPxMfRxayn7O8oyrMFvR"
    "LB61QPJD2orFxWWgmEdeEeRl3oKfnnUeeCTMk/T4zh0iX/vC8CGTY4yl7Hq3lXDlBr4NWh"
    "VKCEpyhyTHtXBa0FLGBaQQhUy+Orgh6cgKUK2VwqqelC2aJ2xIRt6zS2VSsrbfIhlXzdT1"
    "WhkfnUs6ODmqtjx23kEWFafRqDQpwXFdAhT4mGKOW1PlWVbhnkd09jaPB57pg2TXhXO1Dy"
    "2p58adAaEGT47O01jHBwGYbIiqHagW/nI25uBCPm5YHQL4spQwkZXYaL57+GHU32CDdXK5"
    "zsTWjib7gpYWk+JSw9oPKhjd0wJGCgMcX4AQOWiXFZnk+ygIHquDl+9dZoRl+6FbrjLdr6"
    "oTx03bZmGX/p8pdcFZYhydLN8eoZ7NIgG922VpMj2tEuefIWVvks7IcQ95IblV1MZF3Bnt"
    "hjlW5RSlC1jZcSDRWq0UsWwJ2DhoIMJ0PQLgllA5vaMSUD242JsrtEG3HVtn05CQ3Cy3pa"
    "tINgy+VLmax8j9row6x8cll91ihnUpe1Z13WEj1k5eFG9jXuUFs9K6hyvEFHSJQbcWghcD"
    "twa00722084RPdLaI+mJugiAmh8Z2BD4exhgxWuQXmJqeFVRl8IL2ZVXZhZcZYyxUjYBWA"
    "Fyjduf/CXjb78Y+zbYL90CMbDn6J6cdDbSj5rFVDVbFhJD5qVPle7HF77toY4bST0WUyuj"
    "yyKjHCbXAk8uItNDb8tXoNfCfjcQCuHSnHKrM1otErjfBXkO1BNzHbPVZiP3sm0vDlKyId"
    "ffUaLlJlWr1ch+we0DbJRi88wKUe1TovV62dqiWuYw8XDqi8ZTNfM0/zWXkXcyrudfpiOw"
    "+/uleH3nqxil59cH+gJb2myhHzqXLEVDliqhyxn+W2qU+lI+Y/T6Uj9qVaTLboJ2CLniJO"
    "nwzD5Yo4/WW9W4URWVVoLnQ9cM+v9nketnTc0i8GHuF4YE1BTM0EXRY7GtVc1aIQI/90ry"
    "ti6DSHzf2Pxpgui/08XyQ9i5HUqUa3NfKri++xLWGpEcqInmjzNFJhze9k8ArJhfIXtN4J"
    "rus9PbZrVOPbWrqgNhTNu79SeZ6m2jQadEh9IwHp6GudD9btKmd0uvPm9H6OHNNdipOehY"
    "3alFIxI28qqWrWsBotZwlynLTCR60kTFrhE2O4ZFoh+TNwNhdrhOzZ1V5tkI5Jh2uCjk2j"
    "vly3v/bXTTppfBfX+BK8iTNxuFS3PFAjGrvIoR34kFaKFJdfWsMkAeMYocvoFrqMdnBJtE"
    "wJjr1LVNXoZCiIVLPGWyoLeFjQUp9ufU9DOq5M9nn63x6ruxg/uozLg2roUAAMGgNJI+Fm"
    "YbbuBWxJMDqyTG8gitugYtjnqTr7hRzRgvycbgNFRTG+caK2VB0NwrsVL/gBwiVyHVU+88"
    "RD7zBWw7zsKiYn1vzL98C7QSYX5qbmBSykT07MM7QShFrss/KsROEVY6PMTDyuhX+g3deg"
    "DqwWWEXFEAiHP/J8uUT7tW9Z6WGrw95dMoynOUHBsJNGNqkmJO3QZneVHnfv1X6Wul9EVb"
    "+LBffnnqrUJcX4K56letiKMqyz1jkEksmA+ajtWZMB84kxXC4D5nvs7RIA/pash+R/Yncu"
    "tGW2h13tM2smxXC6FJPlv3KCY0ycmkKtGbpR1Rcw7SK6k/XQYGunqq/Boj69JI7EMZ8nnP"
    "bEptGPH1+96GEb3e1C/yegGbJzD5tIuXql9JvgH11crLRe3ARwgtc6UUNXVj6Y7Uh+r9G/"
    "fL8dlay0nkbUiuI04sfwRF5W899wFqYIX9YdOf8N8lEXsH4Nj/Zh5dzdg5M7jpHD94jhbS"
    "l8SMDBFGlwykiDy1oGT6ny8KdwZSUsc/w0HAADlHuUVDqLsM66d8Nf08e8UqcaXwuq1RSj"
    "lyJLldQDhzVjcGbX5H2gvSGrQME3Bq/MMQW3yOagBUAVt6iQdZq232cxRpLbfom/bXtpsD"
    "Wisdl3Q15m1igokhf3oHULMBRJhYTBmTErsmKh7scmjGZ38S6Z+ej7bBNH2d3Mj79Ktr9A"
    "nPxPHPU81CqasZlT7CcoJsE48ur67fXs9u/Fra4HsJMMx1Zn12mInn24Q9HqDoXD+XD6aw"
    "XKdJBFsgTBvw8jmnSXY8Y8yvl/4KiD/Nk8FKKshwOkz8h+WAZJ+Owrxp9x5D/zomX+18CP"
    "RDzNyI+DdsnJU2rTDGW7XgbniuJiEte8ynBrS121Nj8LxIY+26JdigeVqjg9xhEYi5PdkB"
    "4lDdKL5ND2KLhC72iaNtsWAljNqaLqpQo6iKUprSPtBDe7RAaco1JrWX70oPXQIJVuPaBp"
    "PQxoWhOmQZjg5TZeh14v/bdNecFbkn5zXFQ+FnSxpaVToJgcvxgs14CmAIaZC5LlLM/Sz+"
    "FWjgO7gHWVQHWx/vnvnfSXy4HXxBnwXVwxXNcHt6yhFNnwzHOYK9Ascowbk0cuUMWa6A5G"
    "Mc94OfQwPfZ2tNRKgML1Djbo8SzrIr8cx4T8YgUaLYz9Io/e9lWj7ABGeDQO2vQewkki8t"
    "12Wy7qVKNbjVgJEALxolEChAM6b7dtYuV+1qRLWyaY/EuunCykR1CUDZA2OieRrJZLrcMq"
    "1+STVXdhVSiYTcpyNCQSSPj+NoYGVRpZM0qe6mkKJ1NAwaP2L08BBU+M4XIFFHxMqVdcEE"
    "NAn1ztCxvYFSMGpUJV6ae9U6G6SZ9QKtSgBN4zp0XBiuibN8LTjG/v55cWJI9I40rZojT9"
    "Gie9YiV4mvGhNVzajdBWFtKAiny0zXDSN+qhQTY+tA60DiASM7TRMYgAPiyN7/Sup+0aZU"
    "GcbGgNhH5xPgLS8XE2MBQrNjRwlktZPmGLCWJr/AWve1xmdaLLGVy6zQK0HiuzhdE+XBZG"
    "1kh2lhhqNA2RxeuUsonivKvAMmkJYtaR9glXXHVRtNxFWSjYO/tZXSOUzDRjeOCYtRwbzJ"
    "WqSpluqk+b0duEhXAVnQsHMb1zEskWQM56yvSaU3BaDPS7JEg+G+b+q6K/3V24zsIo/Qm+"
    "VhwA/pBy0iaL56M2gE0WzyfGcLksnn8tupbNhWbP6vHVPtvn19qwIwygzd5kPSoB9yF9Qg"
    "ZQWYye4xbKuUf+UmtZ3a9azunNRw+t/MVcKHoJtq/kJTBkjEkWoJ1m8Xabxxh3RyX/PGMR"
    "yb/lw3+D6CLyH3KkE5GAoD5gqZ8hDBxFvht/W4Ybcm/1Qr5JOO5y97wf8zeagaxD17ziBZ"
    "I5UwrQvuAkFR4uh/HmSC+I+JpMmGbCFc+Dbal6HuT77DnRDf3ZLRq0zk9/pEMpKPJlOFn2"
    "vTbblCeJX7tP/i+0kQV3S3Fzspwg09Y8lpFCaPHnJP6RbIpf7/A3+/cyGVinA6lCkEc+ke"
    "th9iL2PuNkVkR3WoGxKLqqmlZxQcvGx35unSbd6DGIFRe5ppR2AFFntq2XXDJsEzT3hW5I"
    "lmJ3RzSz5TZOBLGF3e3BeJozdQjtxYGgvsxNU1Wo5Rq6JCKI9jQ0rI3jAErArrsZkhvQpr"
    "zgRYFWecE9UURzubarXAAiJQHFbwleIzLpb4Ayax8/vmxEo5bvMEoyFw/M2KlRS2ag56Og"
    "jcCDJs9+oD1to/yjC2/P8z5cOMz0AIP/RTEDOdW/Dc5QX48IT/MwPCLkLtcmX8jkC5l8IZ"
    "Mv5Mn7Qm7izeZ1vJrvd4kUo66O8oyQlbnZLNf5+IMukrfXn3bqwtFvbma0Yi2iZU+Cos6D"
    "EfitELBjaZ6OU6T4cHSnSLUKeiHYJDtXMOLxRp4FRHzaiqG3Dfmzy3qgOL9ImGBP7BXZ0w"
    "CRJxo7lPbt9fL23ZJs299mNzfw49tr8uPHDy/fl59/+L8Pty/fyKGBpvEugQNtQIU8AenY"
    "DinTgnxxEzsKXxtvVrxiYaSsZdmoulskeLLwMYcWfClqcJLNsGSN7pbSWMYeeqMC07dtpi"
    "bK36ggTJfk6zFUJVu1Ad/bsqdJKlvXHljcwAy9LDNFbgNmi7dpdT3QIi3n/s1ET9i7J0Pp"
    "597NKkuS0Q0n/KVbVZY8/rqdqrwPl3cmrbzQyiXR0q5xEnp3c4Fmlj+52qeNoWrMIQ2sW3"
    "eY9KeL608DIhNGiUi4J4qNjDjjqIw4Y09GnNFK8dxu+4CYD3+YAC4U5ZirTlG6rzp4dqQY"
    "3e0M6BajL+YLuB+sl7Dyj3q9/P7/88pX1A=="
)
