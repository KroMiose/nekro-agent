from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "workspace_comm_log" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "workspace_id" INT NOT NULL,
    "direction" VARCHAR(16) NOT NULL,
    "source_chat_key" VARCHAR(128) NOT NULL DEFAULT '',
    "content" TEXT NOT NULL,
    "is_streaming" BOOL NOT NULL DEFAULT False,
    "task_id" VARCHAR(128),
    "create_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS "idx_workspace_c_workspa_53c7cf" ON "workspace_comm_log" ("workspace_id");
CREATE INDEX IF NOT EXISTS "idx_workspace_c_create__8d42b1" ON "workspace_comm_log" ("create_time");
COMMENT ON COLUMN "workspace_comm_log"."workspace_id" IS '关联工作区 ID';
COMMENT ON COLUMN "workspace_comm_log"."direction" IS 'NA_TO_CC | CC_TO_NA | USER_TO_CC | SYSTEM';
COMMENT ON COLUMN "workspace_comm_log"."source_chat_key" IS '来源频道 chat_key，用户手动发送时为 __user__';
COMMENT ON COLUMN "workspace_comm_log"."content" IS '消息内容';
COMMENT ON COLUMN "workspace_comm_log"."is_streaming" IS '是否为流式聚合结果';
COMMENT ON COLUMN "workspace_comm_log"."task_id" IS '关联任务 ID';
COMMENT ON COLUMN "workspace_comm_log"."create_time" IS '创建时间';
COMMENT ON TABLE "workspace_comm_log" IS 'NA↔CC 通讯日志';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "workspace_comm_log";"""


MODELS_STATE = (
    "eJztXVtznEYW/ivUPDlVis39ktraKlnSbpSypawlb7KJU1QDzYjVDEy4WPLG/u/bp4EZri"
    "NAM9CS5sHyCPow6OvTp8+9/5otAwcvotenb09uUEz++T5ezH7g/pr5aInJh+YBR9wMrVab"
    "23AhRtaCUthkoGkXRlpRHCI7JvdctIgwueTgyA69VewFPlB8SlRF48lPScWfEgUb0qdE52"
    "VEPhui8SkxdEMgP3mFXFeRSD4rmm7Bs53AJg/3/PnjHpP43p8JNuNgjuMbHJKH/f4Huez5"
    "Dr7HUf7r6tZ0PbxwSvh4DjyAXjfjLyt67dyP/0EHwhtaph0skqW/Gbz6Et8E/nq058dwdY"
    "59HKIYw+PjMAGY/GSxyFDNkUvfdDMkfcUCjYNdlCwAbKCuY31+WsUtG2cHPswTeZuI/oFz"
    "+JbvRUHWZF1SZZ0MoW+yvqJ9S/+8zd+eEtJvubiefaP3UYzSERTGAm6RSXjC+4zr8L0Ngg"
    "VGfguERboKkhYhrEKZA7cNy/zCBswNo+ZoruGtcq4quoSRZFEln10b2M+RarzZjPEWAN9e"
    "Xr6Dhyyj6M8FvXB+Db8HZCWly+zi4/u3Zx9eCd/BZTLIi3ER+Q3SqxBHODZ7MWqJ5mF+bQ"
    "A5w6sXxs0c+ymRsUUWsW5ZmBuXfTcgAh/X8bvG9y0A5uMr2JFX3BeDtoFXknpr+fhoBr0+"
    "+/W6xKAX/z7+cPLj8YdX749/pTy5/JLdeXd58c98eIF/T95dvq2gjBy0inFo3uIvdbDJ5h"
    "M2g10h2xfmHSUsgM2L5KcgO0QyqKpOINd5DTjYVjuy7xLdmwvsz+Mb8qsqb5mIHHZV/q4C"
    "cHZHpLfKQGfbc6NQaMe5TDU9zGvO7i4WRsKV/j4A2ZxuELa7FLlFqaHIPGFkzXB5tkCm6A"
    "wAOadjCmTN1qxmvbYLyJLYAWRJbAUZbtVAjvvK4SLN5NJBEUDwKrbMt1sBigLKm4x5nkER"
    "HfifcRgh+IvMKEZhbMZek1Q5JXjCnZY5aX9MZYqc7Dmv8w9jayqK5RowAw6RNrqjaTBjtg"
    "Vai0uUa0Nx5Y4zE2LkXPqLLxm7bNNizt+fXV0fv/+5pMqcHl+fwR2xpMbkV1+plVlcP4T7"
    "5fz6Rw5+5X67vDijGAdRPA/pN27GXf82g3dCSRyYfnBnIqfA2fnVHLoSU9wF4W20Qjbup8"
    "5XySbX6BVBo8a5IpPPDlbIInQVm3yWJDSZjm8TvonxsFVWJmVuZYkCbC5k3GE1FSY8WTlD"
    "J7xCytqEq6orw1Rb/AuecPry4LhzbwsuKLhgIfv2DoWOWbsTiEHb2PqtpbisXkE+mtO5Am"
    "zhLUv+0/c4ihCVWi0O1nzA0YMO1mVh5KMdrKqjg5HKq+6jHKztjzk4WEd3sEaYvHnY08Iv"
    "EU2vwksOVdV5AfiMVwaa+YKod1DOyahW7ZzeKysLGVJ9Df0KGXMQE0NUE8ChbRkYthFJGW"
    "757xV3z74din2BlEH8CeYYMJcQk/h7EZHiTbi3y+QNxSC7Y8eK0SZcQ+x+zL0NYo5ArLp6"
    "apVMY3oQjEJso8UCN4jrh+JhRcoRI2LdIKZsLCOw81QHF3UElmJkh8DDSF6tTG3tqZaUqS"
    "aHuajnKhg8GYrk8iwFIZ626/ZJumsBwAERiQ0Rs7CzFppYLVDsBuHSTCIc9hMkDaSTw76R"
    "IARqRQTJIkraQGkiKmoHuMmoVrzpvVooIsY+4VR8H9fRbk+CqNJNnwxRktyCroChY4HnQt"
    "GJNFE10X60VrKXxIgcyb5pKFU6lmcg9yxxP11dXrA5DSG6M+0/Cb5Og5hvn4UK2fSToEiG"
    "m0bXuJN/gfmj8wKbiBNMezN9kWZ6rFVRNSAOrSjs51+Bh4TGNKIYLVc9bPw64b5M/UGelU"
    "0IhG6uExn5h/jisw43HeKLL2zC2Yovnt1j+wQ0jMbg4vru0bbIIuEDe62mDAsrku0O7HJd"
    "tsFSx1KqXPQOK3Z7zCGsOHpY8eBcmsC5RL59Psch9Vr0dJ02kI42BbM0bFWbAQOruX62cX"
    "gw5O8oYdY3ythIPJ4ZMrv6EsV42QP4NMGbmQBjlNg2jqKeYbAC1YghsPZ9sVgVJgo8qMgG"
    "UxEv2OUHOPQKREyY1s1KAuPevCCJV0ncwOLtyBdIpsddd0FFUwQw9zTsgLqmGYxiTcSwST"
    "XdPjK8RDRamcisUWjLruauxXWrEj2ZuCbYJPMbWvDt+X04ukY4eTmOygtQ54TBtDVkFwP2"
    "WNhRssJ+/HVxsGoJOhJb5sxPlhT7c/KSyLdxfdcs0o+XnMM3oa/wUACgWqo4IOKYGj2SqK"
    "lrewd+2WbqXL0/fveuvi9SExhcKuayQUC3WohVsonBLO6MG//MK8AXW5BR5qQB1/GdoBkE"
    "UI3UH+Vm4omx1hRImEy1PLawjoMYLQbAXKObWjTItkMdQ+Bz5CULjHhBS9FmAWeyx4VoSJ"
    "iqQDWihdioZhi6ARgbgsp+mOoQSHnWfvVDIOWFTThbgZSfF8nc809BLjeGUgr3j7YFU1Z0"
    "3FrADwynSI4Izg1XLd/tG07p9JhDOGX0cErGJD0DKmWqyUMqRe7aXRhlL+4KOhE90S7SMI"
    "V1cSUbithRWxsL5c9okfRKkytTTe/mbINa4SVGnZ0xConoNofEaBtIJ+d1TcV4LUWeYtg2"
    "xXRI1LZGydRkMBm1PViFz9pIOFiFL2zCGbMKaUfUWbNFmN472moN0jHRcEvQ0HU5bYLa2/"
    "prJz1YfKNbfCFeBnHfAtgS0Z4Cpd0z6FzHJjoA4q0iaw3TBJQuSpfSrnQpNaUL2twRHHsX"
    "0pfoWMshUjQx7U8ggK6LrPKalrHYMX9rnNyivilzzHTjKIL6uK6n+8lL9OJFv1zEnGByZF"
    "O7gRhuOjNOCvSZiOiwj4NiQzG9c6LEqoYE/TV4231loQhnNip77omsGrUP5AUSxjBf166y"
    "iXXx5XvgXSFjC3NVsl1QP7qK5PHdb/OGNIttXp45IxmdJZRTF4+l4VfgZINEC0Vy4afIgy"
    "WqGl3lS0XVE7p0giCj2pU9odYLor0+GKrIWxMv2tIuPvoEkt8dz46PuIUXxX/sRLPuldG8"
    "j2LhvKK+ndurjH1UNt7hAbXDGhICXcP+uaVd0ppieo5P+w1DyzVmFJKDA/NZ+7MODswXNu"
    "FsOTA/YDsJAfhrwg/hT4E1a/Rl1ocdbXNrhvlwyoqh+d+MoIuLU+KpN0MGPVqCvENFpi3r"
    "8gaka2EhYxfEh4jIeKL86XYY+PRTTffe4WN37Br9+PH8tIdvNEk85zXQDFm5D7tIZ39zE9"
    "+GueDoN8EP+e+zxo1yjdL5aYoTvFYz/L0Vk7T5V7oii2uN/uXb/aiE03o6UTcUu1E/hnqi"
    "85Mu0mTbOr7Qgxc72W92+SSTYri7+wxUlZdOussW1eXZdRx88pkG43oGd3u430YKb7yE+U"
    "pQJOzSLj7GY/h9D8o6/kz7qpG/po97pUw1vRVUrAhPN0VVcniwjgyL1nYa3DF5n7RFMrgI"
    "ZKxb65yotTsmny2yOBD9aeVFuDvZJfZURECgx/erXhZsiWjq6TshL8NBlRdsD7pLvZIu7+"
    "aTYWAHrltI5hQOqmQsBW4JaOn53E2QhJyDvnDLwI9vOCe4Y2x9gTr5v8DvKdQ2NFNPTr6e"
    "4ESjdEbOjy+Ouevf8l1ddmElKYYucseRh95c3SB/foO84fOw+20Fzo0iTEJroftMRJVuxO"
    "ImP5v/B0QdHDmVpUJkS0ZAQPqGrAfTDb03dxjfYt95Y/tm9tfAR6KexuTjoFXSJSAotMcD"
    "hVo4MIpRnPRyOG8oxusBszmtua51iRZsI7RFH0xAOvTNCiURHtaQZOcY++AsDhPfRA1hq+"
    "0umgrpDlw0O8zhyPZoC1ZAXQlIOyWm2wi00YAEBImvibQd7OwMOXByNLe67BYoGsoPFVLm"
    "+AEd+KE/Pyy9yPVCbK6ChWf3sn/rlCPukvSbg7wlRC0aqAhwEKdra5WeUZaiQvK3mimS66"
    "e8iW69FRsCO4d1HsJxlxEmX+/0qX1vpR+vBl7iG6vg22ZFsSwHwrIKnxbB55HDzIBOM8cK"
    "Y7LMBWpYE9tByZ/TQ+3cdWNc8nhsJ7D5my7yFgks0O5T1kY+cdcC3YXzbjSMaV29BILVEZ"
    "VcyMIcTYM23YdwGDbFbts9F2Wqyb1GqgZuOAKxsHbJUViLQGddzlXMP86bNLZnItV/yZYT"
    "e1QE+fEAbaP1IaPoHT08UAJG1P0HqoWqi3kjIEXmwZ/huGLuk8qORKspJGkxkox1GC9ZkB"
    "srQL+QItXLVE4OCQXPOr58SCh4YRPOVkLBx4hGxRtyCOido21pA0k+YlApVLF3bc9SqHbS"
    "F1QKNaiAd89lUcARfetGijTT+/uZ7ai8QlF0F4T9Dkor0EwPrWLZap9TisaoHmH6xNAemd"
    "+VI0NZOcTyaRzy14OFG0/5Y6h9wgoTxBb4c1On5NbNrEzEwPHOmiytfWGWbID/BWkT+VkC"
    "6NE0RBcvU7KmihdDBZpKG/W6ab1CP7X8iajhnSxtC/lm4sdew9rZPtUlQsZcM4oNgVnN0M"
    "FdKYoo7878kid6FaYpXOtTPoZMeutDGGOAbOrppJeCggdmoN/FQPHZsPDfJvvbSrxF7PnR"
    "a/ja5gTwp1STdvB4PmsH2MHj+cImnC2P5y9BeButkI1njW7Pze2jbb7Pu9KwDg5QxYFsxb"
    "RgNc216dwJuA/pC3KAsuL0nLZRziPql2ps9bhuObt3Hz219hfNhzI0LF/GW2CwmJPcgDYc"
    "fLTKcozbs5J/4NKM5K/Z8K+QXUT+IyKdqAQE9QGsvoc0cOQ7VnBvekuyb/VCvko4Lbvb9v"
    "fZG3Gg61Ce522XsWBKDtpnHEaNwuVhvAukIyK+IA+M4kaOL4KtiXKW5PvmLbENHe4aDeLz"
    "3Yt0aAVFvmzAkax1yp3krz2m/tcy0nBLvnOmNUGqLtlpRQqhxbdh8D1ZFH/d4Hv927oYWO"
    "bXZ3plmU9ke+BOA/sWh1ye3am5Ck2Mg7OSVC3foFmbx35hnSrd5DmIm1nkNqXbugtZZ8WT"
    "1xRdBctdkBXGSuxuiGVmroKwIbewVXkv0QyK9+x4Btwym6uqyFPPtQwdSiHbU5GwNE0AKA"
    "S/7nJIbUCdcsSNAs2zhntNGc1r3t7UAhAtCSi+hniByEO/Asp2zIZuRLOWbzAKYwsPrNgp"
    "UTPmoC9mQSuuLUHmsyu9bKf8s0tvz+o+LBBmrB9Iu8Qx6hsRKdI8jYgI2culQyzkEAs5xE"
    "IOsZAXHws5CZbLd8F8tj0kko866hQZIZy5XJqLbPyDIZKL40+JKBjyyQlHO9Yi2vbEzfs8"
    "KK5TSwHrSvNygiL5xcmDIhsu6IVglWxfyYjdnTwCZHzqvCLXHfncuBGoQlzEC7HdHBXZcg"
    "BikWjqVNqLY/P60iTL9it3cgIfL47Jx49XZx/W16/+c3V99p4NCzQKkhAE2oAOeQ2kUwek"
    "VA3qxVVs8MXeeFz+irmTslRlI8pWXuCZpo8ZtOFL3oOTLAYzPejOZMYz9tQPKlAdXU/NRP"
    "YPKvAik3w9hq5k8zrgW4/sqZKydmoPMDdMhrxuM0V2g9QXr9PuemBFasbjDxPd4dk9MYpu"
    "ex9WuSaZ3HFS3HQ3nSW7b7eHLu/D9Z2DVZ5b5YxYacc49OybWYNllt052maNoc2Yhyywdt"
    "vhYD+Nbj8NyEyYJCPhkShWKuKUThVxypaKOKVW4rla9QExG/40ARR4vstWx/PtWx3c66hG"
    "twcD2tXo0WIBj4N1DC//pNvLt/8DFMPnPg=="
)
