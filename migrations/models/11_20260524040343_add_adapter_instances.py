from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "adapter_instance" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "adapter_key" VARCHAR(128) NOT NULL,
    "instance_key" VARCHAR(128) NOT NULL,
    "display_name" VARCHAR(256) NOT NULL DEFAULT '',
    "status" VARCHAR(32) NOT NULL DEFAULT 'pending',
    "enabled" BOOL NOT NULL DEFAULT True,
    "is_default" BOOL NOT NULL DEFAULT False,
    "provider" VARCHAR(128) NOT NULL DEFAULT '',
    "provider_account_id" VARCHAR(256) NOT NULL DEFAULT '',
    "metadata_json" TEXT NOT NULL,
    "last_error" TEXT NOT NULL,
    "last_active_at" TIMESTAMPTZ,
    "next_renew_at" TIMESTAMPTZ,
    "renew_before_minutes" INT NOT NULL DEFAULT 30,
    "create_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "update_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "uid_adapter_ins_adapter_d2b49a" UNIQUE ("adapter_key", "instance_key")
);
CREATE INDEX IF NOT EXISTS "idx_adapter_ins_adapter_991e74" ON "adapter_instance" ("adapter_key");
CREATE INDEX IF NOT EXISTS "idx_adapter_ins_status_abe83d" ON "adapter_instance" ("status");
CREATE INDEX IF NOT EXISTS "idx_adapter_ins_enabled_045514" ON "adapter_instance" ("enabled");
CREATE INDEX IF NOT EXISTS "idx_adapter_ins_next_re_74f240" ON "adapter_instance" ("next_renew_at");
COMMENT ON COLUMN "adapter_instance"."id" IS 'ID';
COMMENT ON COLUMN "adapter_instance"."adapter_key" IS '适配器唯一标识';
COMMENT ON COLUMN "adapter_instance"."instance_key" IS '适配器实例唯一标识';
COMMENT ON COLUMN "adapter_instance"."display_name" IS '实例显示名称';
COMMENT ON COLUMN "adapter_instance"."status" IS '实例状态';
COMMENT ON COLUMN "adapter_instance"."enabled" IS '是否启用';
COMMENT ON COLUMN "adapter_instance"."is_default" IS '是否默认实例';
COMMENT ON COLUMN "adapter_instance"."provider" IS '服务提供方';
COMMENT ON COLUMN "adapter_instance"."provider_account_id" IS '服务提供方账号标识';
COMMENT ON COLUMN "adapter_instance"."metadata_json" IS '实例元数据(JSON)';
COMMENT ON COLUMN "adapter_instance"."last_error" IS '最近错误信息';
COMMENT ON COLUMN "adapter_instance"."last_active_at" IS '最近活跃时间';
COMMENT ON COLUMN "adapter_instance"."next_renew_at" IS '下次续期时间';
COMMENT ON COLUMN "adapter_instance"."renew_before_minutes" IS '提前续期分钟数';
COMMENT ON COLUMN "adapter_instance"."create_time" IS '创建时间';
COMMENT ON COLUMN "adapter_instance"."update_time" IS '更新时间';
COMMENT ON TABLE "adapter_instance" IS '适配器实例模型，用于存储通用多实例配置。';
        CREATE TABLE IF NOT EXISTS "adapter_instance_event" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "instance_id" INT NOT NULL,
    "event_type" VARCHAR(64) NOT NULL,
    "status_from" VARCHAR(32) NOT NULL DEFAULT '',
    "status_to" VARCHAR(32) NOT NULL DEFAULT '',
    "message" TEXT NOT NULL,
    "payload_json" TEXT NOT NULL,
    "create_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS "idx_adapter_ins_instanc_3fe82a" ON "adapter_instance_event" ("instance_id");
CREATE INDEX IF NOT EXISTS "idx_adapter_ins_event_t_565686" ON "adapter_instance_event" ("event_type");
COMMENT ON COLUMN "adapter_instance_event"."id" IS 'ID';
COMMENT ON COLUMN "adapter_instance_event"."instance_id" IS '适配器实例 ID';
COMMENT ON COLUMN "adapter_instance_event"."event_type" IS '事件类型';
COMMENT ON COLUMN "adapter_instance_event"."status_from" IS '变更前状态';
COMMENT ON COLUMN "adapter_instance_event"."status_to" IS '变更后状态';
COMMENT ON COLUMN "adapter_instance_event"."message" IS '事件消息';
COMMENT ON COLUMN "adapter_instance_event"."payload_json" IS '事件载荷(JSON)';
COMMENT ON COLUMN "adapter_instance_event"."create_time" IS '创建时间';
COMMENT ON TABLE "adapter_instance_event" IS '适配器实例事件模型，用于记录实例状态变更与运行事件。';
        CREATE TABLE IF NOT EXISTS "adapter_instance_session" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "instance_id" INT NOT NULL,
    "session_state" VARCHAR(64) NOT NULL DEFAULT '',
    "credentials_json" TEXT NOT NULL,
    "sync_state_json" TEXT NOT NULL,
    "expires_at" TIMESTAMPTZ,
    "renewed_at" TIMESTAMPTZ,
    "last_cursor" VARCHAR(512) NOT NULL DEFAULT '',
    "last_message_remote_id" VARCHAR(256) NOT NULL DEFAULT '',
    "create_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "update_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS "idx_adapter_ins_instanc_4cbd6e" ON "adapter_instance_session" ("instance_id");
COMMENT ON COLUMN "adapter_instance_session"."id" IS 'ID';
COMMENT ON COLUMN "adapter_instance_session"."instance_id" IS '适配器实例 ID';
COMMENT ON COLUMN "adapter_instance_session"."session_state" IS '会话子状态';
COMMENT ON COLUMN "adapter_instance_session"."credentials_json" IS '凭据数据(JSON)';
COMMENT ON COLUMN "adapter_instance_session"."sync_state_json" IS '同步状态(JSON)';
COMMENT ON COLUMN "adapter_instance_session"."expires_at" IS '过期时间';
COMMENT ON COLUMN "adapter_instance_session"."renewed_at" IS '最近续期时间';
COMMENT ON COLUMN "adapter_instance_session"."last_cursor" IS '最近同步游标';
COMMENT ON COLUMN "adapter_instance_session"."last_message_remote_id" IS '最近远端消息 ID';
COMMENT ON COLUMN "adapter_instance_session"."create_time" IS '创建时间';
COMMENT ON COLUMN "adapter_instance_session"."update_time" IS '更新时间';
COMMENT ON TABLE "adapter_instance_session" IS '适配器实例会话模型，用于存储运行态凭据与同步状态。';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "adapter_instance_event";
        DROP TABLE IF EXISTS "adapter_instance_session";
        DROP TABLE IF EXISTS "adapter_instance";"""


MODELS_STATE = (
    "eJztffmT20aS7r/C4E/eiLYF4sbEi41oHbujXUv2SPLbfWM5GDgK3bBIgAOCOmbs//1VVu"
    "EoAAUSAI+qJhETI3eTlSA7s47MLzO/+td8nQRotf3h5fP7wN1kKH0dbzM39tH8L7N/zWN3"
    "DT90D7qbzd3NphoCL2SutyJSLh28jNjR3jZLXT/D74fuaovwSwHa+mm0yaIkBqmPO0dRVP"
    "zvQg8+7gzTtPG/noM+7vTQ9j7uTFdd4Fcs+DkMFf/jzjJUPEZHNoKRBoxXXBues3CLdw0H"
    "fmafQ59vhSZ+RcOfCN8uSHz89aL4QfQX2cXRP3ZomSUPKHtEKf46v/5a6vMT+gZjCrWS33"
    "/7jbwSoK9oC6Ph182nZRihVVAzZRSALHl9mX3bkNdex9l/kIGgAm/pJ6vdOq4Gb75lj0lc"
    "jo7iDF59QDFK3QzB47N0B5aMd6tVbvzCuPQPqYbQr8jIBCh0dyuYDyDdng6vXzYNk4/zkx"
    "imEv42W/IHPsCnfK8udEu3NVO38RDyTcpXrD/pn1f97VSQfMrbD/M/yftu5tIRRI2V3hrK"
    "ryvwxaOb8jXYEGuoEv8BTVUWituny+KFwcrkTmlDDWHSKgqe0rZifdzZnm/2VPra/bpcof"
    "ghe8S/LlR7j4r/7/27F3+9f/cdHvVv8PQEbwN0n3ibv6XS98AOzHxlZ/kAxTflzqX5ahcb"
    "oXpmF5DcDEG03azcb0vy+wAzNOUuZ4b5nGeE2gZuavhny9FgQ9YV2ISdUBmjctUwe6gcj+"
    "pUOXmvrnI8f7PddoiyK4mL7TPzDYoDUNQhZVuqZ2KVK8pijII1tYd+NbVTvfBWXbsohr+a"
    "cxg+T5IVcmO+hhmphoo9LHYmHZcvNNRrmrBlGLpqkn9D6mL0U+8edT7/6acf4SHr7fYfK/"
    "LC6w8Nvf7y5vkrvIUQdeNBUYbYQ5TZvLfL4s8Ypue64NlU3d41Op1SVtkOCmzYn12dneMy"
    "KX6TJp+jAKVDdg9WRvQ2bVqwHRuqiz1sUwsU0LADWzZWtzRnYqGwpev7yS7Oljzf+rC+G+"
    "Iyqx5P+oDsNlpoHeumnOXMXKPMJS7871v897SM8QF97Yh0WoKizVDzDRe6BgawwDfUTPTd"
    "f73/6e2/Hb3ffHj1vx9q+02h2u/e3P8vefz6W/7Ojz+9/c9iOGOKFz/+9LxhgZW7zZYoTR"
    "PO3tOt/rqUaN3jJYA1bYcBXgKOsYBp7yHwzkMEi0IxQ4l17/pZ9BktXc6R+xJrL4vWaI8N"
    "atINOwS5+A/FDz2skvsuJwmgWLOYgebBbuSThRHCoWyE+vFmef3m1fsP929+rtnm5f2HV/"
    "COWrNL8ep3zR2qfMjsf15/+OsMfp39/ae3r4hKk232kJJPrMZ9+PscvpO7y5JlnHxZugGr"
    "mOLl4qWayWO8pJYptsGXERZvCV/E4L2xChwMw7njAcxmIRTADFiEt21vai28GyUpWq6jeJ"
    "chTojYCeh1iR+G+E6142oKd2kTR8NQCRLKmNpQFTC17oT0/LskFlgp3U8R1sKyWAFDllhD"
    "9AQL7KSYlKEuwL/A44YvKzyZ3OCnePUtX9NPZJnl28/eVbbbBGMN3hCVzeCmGerEl1du2O"
    "Dky0OGJPzEYP3wguf6n764abBsvZOoSdfY9ltrdd18xY3dB2Ir0C18y66c2qvPKM7mfbJv"
    "dOTdkBTcEpUyRyfidET/hUm0PxdmezDdjNAwujBBCCkBU6HTEx/8iDh64O7Zul//rFHJOt"
    "FflpPQmzJ2583YlXN+mALrUudyjI5J2JWTcnZZVTPgOewiVCktzXYDXnUp4alQdplavuXR"
    "LWEMlGXqPZAsU+8EsuAtXu5nGabJengCqBQTjaOw22Tu20uWBcoVliUjtEyFpNKxDkeRbD"
    "peo+0W+z7D0NhSRLR+a45DYNsy438b99sqcYPB4HdTTiad26GF9w1bsyyZUe8JIbjqgJEi"
    "BLJGjO/xbkntdThmLMbeDYoat4zU8XFjCBWQthcEQ2oo2QArD8IWBCfUoG6SBmH4/IN3Pd"
    "Ooh2vjIkZhX3OKFadY8XpixXzvWILXPChcbAkKd0uYHQGveeVYV/v0YSP2JQIcY0f4Dxrs"
    "BPJkRWuc3TufRvnD9lvs0xk72AAcUeH6555UMusffd1E2MsbkQyvS0pW+mCHvjWlv/P8NQ"
    "pGmLcuKZl52cqWqdKBKWbyd+mWV0nW7TU0xETvoKxl2d3URJpNKyjHeA7Gog9Kh0d1+g7k"
    "PU71WI68LVO0TjK+O3xA99wnyGQG/C8EcC5U9FWIXn//+PxVrBOadANo0lRvcjMGl6veBO"
    "/fGf5/HKPVnAsZsgPu9uGEPh649JmRPbDBKoyDfcDR8H6s6NCA56gOnhy2AzXXiqGxoBsH"
    "uxv7mAlbuzy2ts2rytvqO9QDVsldsAWsT7udGfoKLUI/2jE/YddX4m1R+hktYakOVHZTVI"
    "qWO8MHd83x1XIVh8rxqdeTttmhLeL3fXXuDDWZUZDxKSNPHXkE0/SQMIAYNo4hOFkxXoKO"
    "fvaYKQ8kOYGxq+WvOK4L8QwYPPWHBobOdSnxai5n9si4+Hx6HcpA0ZQbpdtTbrnsrnEc7c"
    "T5lDy0tLMpJ5WSjyvuPH1BHAmbBu7DrIzw3cFYkNyyryvdYdfp+GzOMMuT+DNKt26Wp5fT"
    "bBzW1v0Y2WAYwwudInVtB5YFFvO9G4Zk2hjclyT9tN24Q2tAmmLCPXpjYRE0xICC4AAZUL"
    "dg+FAorLnCfPwJ0b6x1TQh2ldtcPkQ7Td5y0Anov2m6ik4gGgz3QfHI9pVhvEoRLv7MROi"
    "fXFEe4ti4G0aFuHXhMS78BohtyF1x7aiGCPD/LPwauWaGhroN8SkUzEORCmnBanJNU3NGB"
    "/5n1Xvkf9prO4ZUQn1zxJ+Sqj/CHoKeXrv3pMricsxuHQ7RlV+DBodZs+TbIZVbIY2jUrE"
    "hB5YRyny3dVwss+G5AVTYv1UTKaxTkgozQCdtD3xhDmyKfFwIVSrKLwb5pbUpYSrmfVzDQ"
    "RIhqGFikxJiKcN3T5JuBYUOCIjIRHXRJfaZUtNbFZuFibpernbonQgnW1bVLjaqx2k6Ng0"
    "Vc2SqtQ3iTPCioK+cloa9nRrNeTEF0PUdu6FTdiTgDHYNGzSuqL6R3sl52ndzzU5tAylKS"
    "ezBQpkaQadW3KaIXW/LP1/YP3ySte6rdAQE28EQwOuSsiuzV78DcIfu29z6OVb5YZPelZG"
    "vK5N1XQgDw1UbbLXXwFCQnIa28xdbwbE+G1B4X3mLLJSpUDI4SooyJ/yi1edbpryizdmcL"
    "nyi6/WbtTRK0PfutuXU0TlkF7UOS7qx1PKss4YQaiC06HgmWPpQJltmbZef1r35QUX/Fj+"
    "vYb5/ScQOBbZA6K05Q7HkdPNhue+2ZCj/t4oLUdWeNRvqlCYiN1CVExFy/MWxd01gABIE/"
    "5X03yA0mtCor3w12/uf579IlH2WGYYvK1UXrt6Xqny/euXM9hdtb6H//kpArY773fkc4Cq"
    "PZnhSkQ0CUDtWEJwf4xjOz3vy2tMXEXtg3LDsO6pS97kZeAHqbeUEK1dGhQW2vVcaSZtiv"
    "xoEyH4wJZi9wBLNSnRyjUNzWSVKzMFU8DledsfkxUykvHy1NxiA2qpgZfneLVLFHsVytgb"
    "bXtJ8G1wiqImJHoBWcgN2VwE4eHR6CvfgVOoEnzFDSRdVI8uMJNlrv+45u9keytZONJSNH"
    "izHfWWArlRU9fpgjvaDKcsYSlVR6oLB50jPFnRi6HScrEk6M+0G9FQF5D+t01b5lMmipcp"
    "2qy+DeTub4iJtcTr+Pt38GW+/5DI5umnKEQpiv1hk70uJVa578rvMki3l57HIcr8x1GMhn"
    "VJ2WBsW/MsEhSYNwxjtz2pKVF1YwafElVXbXDJElVfkf8CSmH4uari3bu96So8qqynGdf/"
    "ZqqmVV2GhzRaBTO4/63fY6b+t4tnjKYqaAFV0PjTHx5QSlJtA5MbHNGLmWCucENQ20FmgR"
    "lXlbkSFebWdDY0LcoVvmA49P7bNkPrAYqnsf+oVMhZOhF3Po7bhqJcjJR06Ja6IPebO1K1"
    "ZsEpP6LynBESnX3e4yRIXnae7LLNblhKihERr3c7BBfNWEC4Z6EA3DXLkVTXeBsmxKarIX"
    "t4TehifGZdNw9ZYblddzrRwrZrrJvdwyOhgo4GXXnTEhTOG2cqCyDkQxDaOnqI9tXNyTG5"
    "t1my6eiOw7HMq3i3JrovLgBsn5qs/OW6yBWe9g3FoJk5dURrHA16NNUyy3gHftkX6rx/c/"
    "/jj5zrrSEEBkhlueZs0J0RYlNMsDLZk7HCZyDZ6SG4z94J1J65nVNX6+cqANq84VrmCwvW"
    "tWWQ63qIlyeXrrMkc1cj1NySE7016H5AgCHAHBUo3sJunkW1LYOe8RmXumP6qRgp4Xlh2w"
    "EdOwtT/n6qKZFy1bj6lEi5MYPLlUj57+f32y3K5tw8SvHm3b40yidv6ZajemRRWE5ly4JS"
    "Q4CeSyrAgFbsuIDULXStni7puN/6FI88nF35FXiSUAx/N1l55TWmu+0cD/117uNl9JCkNF"
    "uQpGs3oz09V5GSYfV4YXbdPfyEyS710XLj4pC/pc09teR1sdN4I+MVmxOHeaEzw4tpFXmp"
    "m357FkYrUtFj2poDYxCkC0PoAKe9ZyZylHpVmx3ATX9GaMtTXRXDMlhF/0QBQVIHW6pLXj"
    "h8wrfZD9X33WM52/HhX00hlC3gg9INjNryOCueJUUEU3FwaqgmJB7Gregq2qWgcimam6Y4"
    "oGd5shSMalnWirFqPj3z0xoifT6MuKdrjhWSScuzN+CYHsuvdR6wPMpWw5LJhYB4BbM+I6"
    "2PGNtBpxpGr33C2LNPGC0yLdbT7FuXwsiIxl9qLrlK+unx/B2j3jOUn7gPHPgQGgQ6Zm0+"
    "vqHTX2L81/4aRH52N1tF2+y3s2n4/4S72AfdzrxdtMqiePsDfOC/H9Q8ndiWZyG2F+JoFK"
    "yg3upGwZqA1109pIYHtJI/u/Xa5U34bsiREZFpvps68Erg3URStqw8OBp6QjbELqjx3WaV"
    "uAFX76ZFr6CHSEk2BsocIRji6ZUS4g/IvOrEJq2FtuYPubL03JqtwzQD6qrqgmcrrWoBA3"
    "0u4jUW+oLcXwqbh+16pBhlQUj2XUpDDoaAy3qtQG2BZCKLr0jqx88KqGzAhG9LXnBb2aA4"
    "AOVxDaN6QdHzY6kexDpKX/bDc89+FpYcsn/XxSRRNMxl2FoWhnyKLnhRH93tIEyrKScafu"
    "xERhhmVUP3Ae5CSs/Ct3M76U1ccKgNuuSFO4p7oUHZrOA/7uJPS0KMNSCZ0ZASWm5Bvsus"
    "yAg5C7+vC3PiogoC4m3xfOR4LNFDpyprYqKrsNitw1Fhuvq9PUKqTkdVNc1SFc20Dd2yDF"
    "sp9dp+a5+Cn7/+T9BxbSK3lb5yt9ky/ztHtCVzxCVjdTEt6O+xQ9ICwZykQ3PvTyTXXihm"
    "b3UFsRpK04TDPtWNJdSlhGefWMM6xoLceIskLdud6peuupxlql+6MYNLWb/0PKIx5L4ypm"
    "LMXZ9qpqXHjO5T1dS4gLqAZPqXJrFwDr3a2vJDr7vm6ewfyKUwbt4CTpXFYS8+NPRKiqIq"
    "JUpTFCXyfvcx6Gfn8SrLne7lxO2vTFZEvCKZLUFYEd/kEN6IfzA5hDdmcCkdwhcA7O11B+"
    "mIfs6gX449aYE7i8kYKhRjGJZhnaDM/dCD+bdTMGcWxWjJkuB4dntHXoljxxyUZKZI4949"
    "dW+EvbRCBm+Emb/9NdqQEn8neb3JBRJ3jm1BYIdsQSmNR3y84c8bXPLflBOdkqvKP8neqx"
    "KK7aPr9M/SbeFjpUIOPx2WjmOFRDc/ewYpSVRJO4tlFXlpQ9GBF8QJh3EknHCXwEpC8ZBN"
    "lxWRSKsFhY0RitdqlnxC8eD8cUNKsG71UAN3zHOsGflieTJZjELR2kMB2T1Tmg7qXWnVFD"
    "xTiqunl/C3IHXjDOis9cWC5uVH3mV9hqKHCb645mh2gi9uzOBSwhclp/98H4RRjbrrBWOk"
    "tfEnhTLovch5oSahb+uTwzrx47mwRt6YwMbA2NnFI5Z7cldNIdLfzxW7EriDVa3twYYAHc"
    "vSgB4cI/bULkdSOARCSWnz+IZRfN4eLh4Uac70Ac55W1K4umm7hJSKZr/rAHe9ISYaIqlv"
    "HsSnMKEWgV6qbGp+CMVqocIzBbvL2za0axkL3SCXMJPufEQqGxyPrUcfBbgoSh/ARVG6AR"
    "d4r9VpBJ5E23SH2owKKdnomy1DWxSnqoUCsNsCLGCocA027S8yA91jiQD7WeMyvUZTcHbV"
    "vvoUnN2YwWULzvamlftllAflkttR0cCc8fAHcIMo/NQdudqxT3q4WUnGCpNAqjngOnPIcq"
    "WNp6rAU7vu9SXRU58NKeHqZLPxVU//lI0/8uxm2BGmbPyUjR8ylads/JSNF6LVKRs/ZeOn"
    "bLw08f8E+BTqmgCf2zG4bIDPyzxem3dgPuX7dwdgn4AdOAr5qQcVPanxxz6mV/Mny6N+GA"
    "Zi2NX4KFBBUMp9tyDU571XY+K/GvxIYEA+wUgXcxJlusLgmNOrRog/XV6wT144fUzdVtOl"
    "BdOlBdOlBdOlBZfT8nRpwQU4madLC06demADp+nSggteWjBdVHCxOT5dTnBaLa/deOeu+L"
    "qeLie4yEE4XU5w/ssJNF+dLiGYLiGYLiG47UsIjmghmS4hkMYW0yUE0yUE0yUE0yUE0yUE"
    "0yUEPQ07XUIwlYlNZWJTmditl4kd5G1pD7zrWTg2gr2ldUXA/mqwcRwuZ/mQfUwujRaqnH"
    "Gi1mR4sBaN8yhuZVnXw6+kwExy1pdrKTZjm+w4hWeEKMOmU5JU2dv+jE48+C30afuYR+oR"
    "/LJZzzN13urDj+rLj3GeSrZxfZF8YeGW28/UI0HDJGeD6q90vrBwpXfx9Uig7omvhz3LJ7"
    "6eia+HvDDx9Uxx+RSXT3G5ZHH5G7R+FWdR9m3Ojcart+/2xeBrtF6ialyPwLsIpUgE7DmI"
    "eOgQB7vqgl/l00voY4z/R0rf4Hj2ULHl6wiAWFbGVm1gRlAga0oPdXp440MaNUbSMF1Vaf"
    "C9IBGgWj6TZv9wQFIP000L/DG6ue0J2Q+G4b4bJ3Hkuytac88Nwanq6Tq/pthbR5oHe4SK"
    "pnj7xAFEZ4yN9W06OpAseB5ZQ9DqYui+yLCZnd/ckOJVvFsTxb/G38PN8b96iVL9EecKL/"
    "rrn9lgjqzx79OvsuhuV1m0ulWGdgSduxlolFKhMYVQhSjFvGbrZwbM5fN3BzW2+AGab0sK"
    "twGnMqZlidpJq8E+4yz8oDxFW6erVNZyV5G7RYNaCRiRp9FNQJ0dariqm4CaD/7MshLHQm"
    "Dt/va5dKsBdlmRm8KJMLj8iSd6udKdBdcsC/AmLY3ETx74vOKYe3I0+jHiKbXfmdx4xAUh"
    "v9jlTnvqb0JrR731wNQCmOtOnjywY/eZP8whqm1LfXryujvyWv140XYZxTjcij7zqtIOoH"
    "as5OUK5nsBd0YQQiWUA/CdGWg9naPLgHKblZtBOwd254lnGQ07EDrEn8bhYAeIVLda5IQn"
    "EDgCCFxHYUAsSBJ5il7GEzZEwpZhOAWxm+l5hsynxgS5XjUCN0GuN2Zw+SDXTbTFv847Md"
    "f8/buDoCsz8CDqmj8VO++2YrjEv7froCoDpPKLmcY9YgzumaTRQxQv/Uc3W35CHYxXsKJy"
    "Ktju94HSlPsu6/5MsOkJooObhE3FhF/N5cENwfhK5YiKJU+tNhU26LIV3SUdKg4h6YAKes"
    "XQRiGkEwtKh7qPZEA5A7oWuynWAt6RlyNYIrjC8qjb0AKHwJ6e/CwSzMk60CGuS16k02rw"
    "PsMytd9yk1XpH42xMZ8qXhILs6zxt2zhDV6HkR9t3DjLKzSwKzUMq+p8wtOAq1jijSpBiB"
    "23mfxMSVj37kPqbh5HGK0u+FRspRBOQcg+5QXNBCq0dS14IhZ7dLdoucZRe06V0dtiTUGZ"
    "LAYfy7eYY2pmYSVD1ZS2xXI7lrCwnHbzQPtfUPTwyHF4/mOVuB0uZ0OuYbQQBM9lqMUPnP"
    "5+xtu0SLLQhr4a0wISc0iyH639lz/98vzHV7Of37168fr969wS5ZFH3qwnT969uv9xylgJ"
    "z1hdy00rjXxSed0K24IxJpqd7l2ZskhTFmnKIj2hLNIbFETuO0TLaOZduaT6qLtDGaU1DM"
    "dbPTN+aDm/66hl7Ty5uj6vould2n/wAbTM3woXGikpgHIEZ+EWI0xSpM9K1pojLdUvCgvZ"
    "Pj7aBEAjRFpiFYb4mfHih1kXx1q9epE+wFGskDT8BWVVo6PQf+HU0hXzY6ySRzIdg44eIv"
    "I9AiimUN3y24SmSjvSahoCwj3khTlZ0PxjrMEDIcSdgQnL4G9WtCTYiqGPTcTRCUF7C3hZ"
    "tJJzIS+TmzJp8ymT9oQyaXLRQ46fq+x+x25XsPfN3rw0nr3/671qmLP6BpaXxhPyQsMnHA"
    "yGWjZMja1wPL0zzexCXBsdrjatP0F0Vqh+ysnWAbK3h787/3aKHv7T0a/dv56xPd08L6A6"
    "/yXNwt3gnQVPsMvgerAVQ4NLqhxFcYrlwiIsLDelbGgLrWpxV0vgWh3aR8UVFs4e+XSutu"
    "Iz4p6RDvekJJ1cQtzSNSIV67RbXFwHbBCtUbzFX3nQcVCXOsGhcNLZbULMa6m69Yx0DZpF"
    "mZfhQ5+N4YV2aQPHVmf/+hIF2eNfZrai3M0eScYF7yOK8qfMJ0Owg4Iknhe1J6fECo1MKJ"
    "3SUI4VanULFRCgVa4SywkGrY8zJ5gE3QV3Oq2f5Pa30x+yTayn/5bPkRTcTMnh7RLcUhlG"
    "6TZbbhGKR7Cct4RlyyE4jmMWOq41st5qPqGdQCLs5SPt35SVzfyUCh27rmgyf5VO4m+uq2"
    "RQ6VBL8GmE/3xm3X3hP6RXTEMhlUYmy64/e0ubBxYy+4JTPcBVr+epHuDGDC5dPcDPRd53"
    "3lULUI24O1QHsKkNHVgCUNWADkj784Voqt9ULQLUW0GBUVZ3KJZIJWmvocl8FuTPKXtJnR"
    "77eSwlbJ4asDWbvFuVFSguYY4yKImvdiSXX/IQR6Q/qTudjnWfpN+WefnF4b5VLh/gZ0hM"
    "ko1hysbPp2z8ldEB1pdIS+t7EJ6moHi2NHb/Y5pf5WMZauxdXK0fTsK3nyKBCVy9uJGlwt"
    "uoCSi9QuQ/2yJ89GbREeY4fZL+E3ZDVih4OM4i7acItwh7O45slRF51U9b291VEYyI+KoT"
    "dsOh52lOl8lUDOWQvgfOk44U0rPsuQWFI+tmnSTYPkvlRGf3+J6blY/sGT9lzsXybIUshI"
    "BtFefyZ4YInCIFylwMH/zUkqdu3KUSiz4XMONR3ZdKLFpXMDMOacsg+wPhuqRMvcZFJ3+e"
    "OCa34OTVRmVEXCWRQ2dWHCaQ11Etp2DZpEXCpXlPsJ4kipp79SjnJEbDXOi60JmKCEZcXz"
    "UrOvBE1bMWiiENpWO9gtZDhO+IhqXas6q7UUdqUITtVQ+qHD7CtfSSSt1DSvJdKYriMMHB"
    "3Oh7oVtPkPJqaJo2ozXZeQY1JEUytIvlhvktHt1VuFxFIVpuEf4zeSwJnUcIV/ZyVQmWqv"
    "AXnQbEV7ZtkUW3GF1jc+qDZeranrq2x3pIfwtSNyZ3dZblxDmfh5RlxMtPEY8UqZ/v1HiE"
    "+JifBRZlw1NyZQ2c3XUp4b4pq2C2qoHu22Zgw7+KGb5++YzEi2AB1V0Axm55uiPZBRfXRC"
    "3ZBLxcqwjSaejAJ5ksWlMAghy1TM5BOIn3msckXa63D9xAudsoLUHRJnGMBSnwdtwqdQvA"
    "FS3gqXU9lEunfzh95gOips0uhsSexuikSRQQXnshoLpeENCa/DIdzzIlym4NLpNhX1vw6Q"
    "zlsUSN0VBaS0CIjGf1etO1NLrv2+l8gPAOoV6LgwF9TVXrS1R84hitpUTukuhvA/6ikMcC"
    "fJpPkRbAse4mTTLkg15amj8UJtdEZbhJ29ACaI4LQfGm6pZ1uKavkRQUUJvU7tNGwOAINC"
    "cyhdFYs2Ga/BNx+rAOWaSSk8IcC88rZr2lemZBdlPUuEGXoqFAFQ/FjwwcaMtkiLUb79xV"
    "DnIvA7TK3EEQeYf8JaFyhQ+Vm6ruFYvA9uH2Q9Ow9LKysATP8RgbKIacU1jmZEB6rlfX5z"
    "crdvtQfGnhTlQXbM5aydTBGrTm7ThYROuTMte6M+ZaK2HeVuvYBAfvIU8kx9FlrFvOdxT0"
    "bOGgRvC61BNpDyqZy0qUgMsL9zR4oafmn6vuBZmaf27M4NI1/7wrChnWKM5+TB7mXT1ArY"
    "F3h1qBUlai6DEdzApaK1hAhEEIQsv+rKAHH0BbhWymldT0gLaoXTFh2zqpbdVKpk22pJLl"
    "/VQVUplPMjs6hLk6crxGHxEi7NMIAuKcVECHPiVSopRzfaoqWTJu0P0YQ4PX88S0acJ3tU"
    "Ml5/ZkqUFrisDDZ2/vYYSDyjJESoZqh4Gdj3jxgjNiXm4Iw7qYMjfFo8ty8fzXqOOSPWzN"
    "hweU7m1oYk+4qWFpPjUsPSH60MZqGFMw0HiE+IIBy0SopOeTrGCg2m76z96ajPCpW2lX3K"
    "Stb8pj523rKeKnLnvIVWUZkkzdXF8Di10aYsKxtZof0a52yZu3kMp2YT+FupccVPYQ9nU5"
    "a2IPKt2SlIC1jfUSDRXY6CUr4M6V5oYZSsdouxSUTdkEx5RM2V6Cg92lu+aztu3rSWgIXj"
    "bToh1Utly5lAnlu2rQh6J8cqE+Kzc3Uhfasyq5RA+hPMzIoeAOweopoUp/QIcrlIM4hAjc"
    "Dr3apZ3tazzhFd0rqj5omqCoCSH1nWEAm7HmGpS5BZ6NdwurAnygvZkyu1CaMXrlihFSBu"
    "CFu915vyM/m33/77NNioLIxwsOfknIy2MxlPyp1YWqfGAk6TWq/F707faza2O4j51Alwl0"
    "uTKWGO4y6Kl5/hISrf4aXwN7k7EYBde2lL7BbE1IONMIewTZPtwmZnt9PfazdyKNn748Ue"
    "Gz1/BcVabZy9yQPUC1TTHhxANM61Ht5uXqaqdqiuvIR0UCKr+ymeXM0wJK72JO5F6nJ9t5"
    "+uxeHXHrxRi9huj9iVJ6TcwR84k5YmKOmJgj9pvcNvWJOmL+l4k6Yl+rxYRF3wAWPVWc3o"
    "zB5ao4/Xm1e4hiPKvcOTf1wLx/ty/zsCHjlkExsEfigV4KYmomxLLI0UjkqhZEjOy7e1MR"
    "Yx9zGO6/GjBdFvw8nyQDyUjqUsKxRnZ2sXdsS0g1QgwxUNusjFS6ZlcyZIXk0vJnd7XjHN"
    "d77tiuSYnHWrpUbSiaf3xQeZ5LtUk16Bh+I46o8LnOFut20Rmdbr85fZ4j1+lui9KBxEZt"
    "SamMkV8qqWrWOI6WsxQ5TlHhVQcJU1R4YwaXLCrEfwbK5vyIkL53tzcaJGO24yNBxyZVX5"
    "43PPrrFp0ivotHfClaJxm/XKrbH6gJiSY5tMMA2kpdxWOn1jhPwOjjdBndTpfRLi6Jl1us"
    "x8EUVTU5GQiRami8pdKChwWh+vTqaxracWXC58l/B8zuYrxwH5dVqqEDARhcDCSNh5tF2W"
    "qQYksB4ZqlcQMO3EaRYZ+HdfYz3qI5/TndAEUlIR6cqE1VR4PybsUPv4NyiTxGlQ+eeOo3"
    "jNV0Xt4qJqeu2S8/QN8NMbl0bmp+SEv65NR55j5wSi32oTwPvPIK0VqmEI9noe/I7WvAA6"
    "uFVsEYAuXwPfeXS1y/9jUrM2x1tXdThrEyJyAMO2llk2pC0w657K6K446e7Wfh/cKh+mPC"
    "OT/3sFKXEuJnPG31sBVl3M1a53BIJgDzqvGsCcC8MYPLBWC+Q/4uBcV/wPMh/a/Em3OxzP"
    "awu32wZloMJ1MxXf6eC/SBODWFoBm6UfELmHZR3Unv0KBzp+LXoFWffprE/JrPEz72xNDo"
    "L7+8fjkAG93touAHkBmzcg9DpAxfKfkk+Efnk5XWyU1AT/C1TnShK6UPpiuSXWvkL9+Po+"
    "KZNhBErSRO436Mb+SlnP+GszB5+qW3I+e/QT/qAuav4ZN7WJl09+jmjj5++B43vO2Fjyk4"
    "mCoNTllpcFlk8JQhD7sLVyhh2eOnoRAMoBxBqXQWZ53e3g1/zRB4pS4lPgqqcYqRQ5G2Su"
    "qhQy9jcGb3+PvA9YaUgYK9GLyCYwpr4cVBCEAVr2DIOs2132cBI/Fpv0RfN4Mi2JqQaPO9"
    "wF9m1iAUyck9CG8BApJUaBicGbOiKxZ4P9ZRPHtMdukscL/N1kmcPc6C5Itk6wvcyX8m8c"
    "BNrZIRbZxiPQGZBLXI6/u397MPfy9OdT2ElWQ4tjq730bus/ePbvzw6Ebj7XD6YwVoOvAk"
    "WYLjP8QQTbnLGWMe5/Y/sNVB/2xeClHy4YDoM7welmEaPfuC0CcUB8/8eJn/NfAjdk8z/O"
    "OoVXLyltpt5ma7QYBzJXExj2tedbi1va7aNT8Llw59tnF3WzSKquL0Oo4BLE53Y+4oaYhe"
    "pId2AOEKOaNJ22zbCaCcUwXrpQoxiKUprS3tBCe7RABOr9Za2h89aj40RKWbD+40H0ZcWh"
    "NtwyhFy02yivxB8W9b8oKnJPnkpGA+5txiS6hTgEyOnQyWZ8ClAIaZO5LlU55tP0UbOTbs"
    "Qq0PKbCLDe9/75S/XA+8xu+A77KK4XkBpGUNpeiGp5nDPICmlWPMmLxygQTWOHYwiueI66"
    "GHxyN/R6hWQjda7WCB9jdZl/jlLMa1FyVotBAKij56O1CN8gYwbCMx2ibnEEpTXu62G7mo"
    "SwlHjSgFCFbxokEBwig6v27bRMpxaNKlkQnq/+IjJ4vIFhRnI7yNzodIxuVSu2GVueSTsr"
    "tQFgqKSVmO5vIcEvZ+G0MDlkZ6GSUrdZvOyVRQcNX55amg4MYMLldBwS9bkhXn1BCQd+72"
    "lQ3sihGjWqGq9tPBrVDdojfUCjWqgffMbVEwI4b2jbAy4vF+dmpB84g0qZSNu91+SdJBtR"
    "KsjHjVGh65jdBWFtIo1Q3cTYbSoVUPDTHxqnXg6gDsMcM1OgZ2wMe18Z0+9bRZuVmYpGvC"
    "gTCszocjKl7PBgKyYkODZLmU9AkbhDW2Qp/RasBhVhe6HODSDQsQPlaKhZF7uCzkWoJwlg"
    "Q4msb44nVJ2VxxNlVgmYSCmN5Ie8OMq54bL3dxFnHWzn5T1wQlg2YMHxKzlmMDXKmqxOim"
    "etuG3qS0hKu4uXCU0TsfItkEyE1PjF5LCk6TgXyWBM1n49J/VfW3t4tWWRRvf4CP5ReAP6"
    "WetAnxvGoAbEI8b8zgciGe/1PcWjbnwp7V23f7sM8vtWE9ANDm3WQDmICHiN4QACoL6CmW"
    "KOeI/qXWtDqOLef08NFTo7+Yc10vzvKVnAJDxppkjra3WbLZ5DXG3VXJf5nRiuQ/8uF/QH"
    "UR/g/e0rFLgLU+YqqfoQzcjQMv+bqM1vjcGqT5pqDY6e773+ffaAa+Dpnzih9KlkwplPYZ"
    "pVvu5nJY34zoBTW+wg/cZtwZzyrbUvW8yPfZcxwbBrMP7qh5fvotHaig8IehdDn02GxLnq"
    "R+7Zj+X7hGFtItxclJe4JMW/NpRwqWRZ/S5Hu8KP71iL7af5bNwDoZSAKCvPIJHw+zl4n/"
    "CaWzorrTCo1FcauqaRUHtGx2HJbWacoJr0GsrMhcSmmHUHVm23ppJcM2IXJf6IZkLXaPOD"
    "JbbpKUU1vYfT0YK3OmG0IHWSCsT3PTVBWCXMMtiS5Uexoa0sQkgFLAdddjegPakhc8KNyH"
    "nHCPV9Fczu2qFwB7SSDxR4pWLn7oH6Blen28eN+IVC0/IjfNPDSyY6cmLRlAz1ZBG6EPlz"
    "wHoXbboPzVlbfnfR8ebGZ6iCD/opihnOHfGmXu0IwIK/M0MiL4LNemXMiUC5lyIVMu5OZz"
    "IS+S9frH5GG+PyVSjLrrlRnBM3O9Xq7y8QdTJG/vP+7UhaO/eDEjjLUuoT0JC54HIwxaJW"
    "B9ZW4nKVK8KDwpUs2CQRpsip2rGLE/yLOAik9bMfQ2kD+7bAaKyYtEKfL5WZE9FyCyQqJL"
    "ad/eLz/8tMTL9o/Zixfw49t7/OMv71+9K19////ef3j1Ro4IdJvsUtjQRjDkcURFJ6RMC/"
    "rFTeQoLDferPiKBUhZ67JRda9o8KTlYw4hfCk4OPFiWNKL7pbSIGNP/aICM7BtGibKf1EB"
    "1mjqdpTR7SHSq0ldLF7nrwoLBRAPWkCQl1PONiLEGQRoFCIu9q9nzJZVQsWeYc9e+D+nyX"
    "qTvcFxscxt6tF2iT8eAZ3cQ9t0e+9aaorKdt0S7EqwivSSHwwf4zSJYlfmdo6/BfaEly5l"
    "7vbT4FtGSxHhiBfrLVWUoP39pImef7yjOsEpBZwiX3j9DlE3cL4/vi6H3fULsFN2/KgaRD"
    "vQ9cIVpKzqOoKGq6qo8ONOUxS1FXkf+7DbCcmlqVMsZsvQCKYpJ7pu0XI1rZhg7JRzDLUn"
    "iH+Bc+bJ3p5YW8RH1YOeh1EYraEzePAkbsoJd5XopmhaVjh+5p6+rKdc63GSceZvdyjXEh"
    "QNctTmsQOM9KaPet5beekgrFQe3CW3/H3LA/a6U698aZmSsPCB/CQsa6XqyjrizVqUFP1o"
    "i50lLVvqfEOi/FErpRKVaa1UhGtyrpWt/4jW7uBF0hB7GqvD8Ayr4PyvwVOlcy3n6tjsvF"
    "XkLzfut1Xicrz1bjO1JWWyVHcxiWMZ0Ipl6JB7XNA7qirbGYp2PMp0FkttkZ+irND3EsV+"
    "+m2TIY7Nuje0fc8QvbMZqqsUzEOUjJLegHJWS50HYY9BOxzD7MVoGakLwrNlsLEHncX/hj"
    "THJBP++tTgwancaiq3msqtnly5VQH0PseGpXboAwsXo++GocNLj5EbhRLrCE5ONkrA3uii"
    "8ENp0sfywyFY8fBHchDjX1v1QuXfjH/9rQEot0dvkzRbJmmAn4bHtt8vTs/fJiz6bioP67"
    "NWhJWEsRO/vz4bUsLVWe0HwhQ5+dmX8LOZnbf/bK0LCb4YxNQcuOYA2T2beE49T/kA/Z4E"
    "kyS4/FAs/gKkqVPQd9UxwBT03ZjBZQr67lEa+Y9zToCXv3O3L5hzqzGHArfuzo/bKbWRpv"
    "tlBK+MED6ZI7XYOJqNXkezsedoNloE/ZvNECXmw5+mAheK0qdeRlG662XgvZ5NEN05uO4m"
    "iIsl345T6yWSaEKPlz//P0383r0="
)
