# en-desktop 账号系统：小程序个人资料 + 桌面账号打通 design

Date: 2026-07-24

## Context

`en_desktop` 后端（`service/en_desktop/`）目前给两个客户端提供服务：

- 桌面端（`en-elctron`）：账号密码注册/登录（`auth/register`、`auth/login`）。
- 小程序（`en-mini`）：静默登录（`common/requestDesktop.js` 在请求前自动 `wx.login()` 换
  code，调 `auth/wechat/mini-login`），后端按 `wx_mini`（openid）建/查用户，昵称固定写死
  "微信用户"，无头像，用户全程无感知，也无法编辑资料。

`EnDesktopUser`（`model/en_desktop/users.py`）同一张表上有三条独立身份线：
`username`/`password`（桌面）、`wx`（网页扫码，开放平台 openid）、`wx_mini`（小程序
openid，appid 与 `wx` 不同）。三者互不关联——小程序自动创建的匿名账号和桌面端账号密码
账号是两条完全独立的记录，即使是同一个人在用。

这次要补的是"账号系统"里两块具体的洞：

1. 小程序端完全没有个人资料展示/编辑入口（无头像、昵称展示，无法修改）。
2. 小程序（wx_mini 身份）和桌面端（username/password 身份）之间没有任何打通手段，
   同一个人在两端会变成两个互不相干的账号，数据也不共享。

以下设计已与用户逐条确认：资料编辑走微信官方头像昵称填写能力组件；账号打通不是"来回
切换用哪个身份登录"，而是服务端把两条记录**合并成同一条**，之后小程序无论静默登录还是
过期重新登录，解析到的都是合并后的同一个账号，不需要用户手动干预、也不会退回匿名身份。

## Scope

**包含：**
- 小程序"我的"页新增个人资料卡片（头像 + 昵称，可编辑）。
- 小程序"我的"页新增账号打通入口，覆盖两种情况：
  - 用户在小程序里是第一次接触、桌面端也从没注册过 → 直接给当前这条匿名记录"认领"
    用户名密码，不涉及合并。
  - 用户桌面端已经有账号密码账号 → 把小程序当前这条匿名记录合并进桌面账号，包括迁移
    自建词库和收藏数据。

**不包含（本次不做）：**
- 手机号绑定/验证码登录（`phone` 字段已存在但本次不接）。
- 退出登录 / 账号间来回切换 UI（合并后就是唯一身份，没有"切换"的需求）。
- 桌面端（`en-elctron`）改动——桌面端的账号密码登录本身不用变。

## Architecture / 数据流

```
routes/en_desktop.py                新增 4 个路由，均挂在现有 /auth 前缀下
service/en_desktop/auth.py          新增 update_profile / set_credentials / bind_account
service/en_desktop/avatar.py        新增：头像文件保存到本地 static 目录
model/en_desktop/users.py           不变（nickname/avatar/username/password 字段已存在）
```

头像存储沿用 `service/en_desktop/sentences.py` 里已有的"生成文件存本地 static 目录 +
拼公网 URL"模式（`app/factory.py` 已把 `LOCAL_STATIC_DIR` 挂载到 `/static`），不引入
新的对象存储依赖。

## 后端接口

全部要求 `Authorization: Bearer <token>`（复用现有 `_current_user_id` 依赖）。

### `POST /auth/profile` — 更新昵称
- body: `{"nickname": str}`
- 校验：`1 <= len(nickname) <= 50`
- 直接 `EnDesktopUser.update({"id": user_id, "nickname": nickname})`
- 返回 `{"code": 200, "data": user.public_dict()}`

### `POST /auth/avatar` — 上传头像（multipart）
- 保存为 `{LOCAL_STATIC_DIR}/en_desktop/avatars/{user_id}_{uuid4().hex}.jpg`（用随机后缀
  而非固定文件名，避免 CDN/浏览器缓存旧头像）
- 更新 `user.avatar` 为完整公网 URL（同 `sentences.py` 的 `..._PUBLIC_BASE_URL` 拼接方式）
- 返回 `{"code": 200, "data": user.public_dict()}`

### `POST /auth/set-credentials` — 认领当前账号（无需合并）
- body: `{"username": str, "password": str}`
- 校验同 `register`：用户名长度 1-20、未被占用；密码长度 3-100
- 直接更新**当前** token 对应用户的 `username`/`password`（hash），不新建行、token 不变
- 若当前账号已经有 `username`，返回 400（"当前账号已设置用户名"）
- 返回 `{"code": 200, "data": user.public_dict()}`

### `POST /auth/bind-account` — 合并进已有桌面账号
- body: `{"username": str, "password": str}`
- 校验：`username`/`password` 匹配一个已存在账号（复用 `verify_password`），且该账号
  `id` != 当前用户 `id`（否则 400 "不能绑定自己"）
- 合并逻辑（`source` = 当前 wx_mini 匿名用户，`target` = 校验通过的目标账号）：
  1. 默认词库（"生词本"/"复习本"，靠名称识别）：把 `source` 对应默认库下的
     `word_library_items` 迁移进 `target` 的同名默认库（按 `word_id` 去重，跳过已存在
     的），迁移完删除 `source` 的默认库行。
  2. 其他自建词库：`target` 下无同名 → 直接把该库 `user_id` 改成 `target.id` 完成过户；
     有同名冲突 → 库名追加 "（微信）" 后缀后再过户（保证 `uk_user_library_name` 约束不
     冲突）。
  3. `word_library_favorites`：`user_id` 改成 `target.id`；若 `target` 已收藏同一
     `word_library_id`（唯一约束冲突），跳过该条、丢弃 `source` 的重复收藏记录。
  4. 把 `target.wx_mini = source.wx_mini`，`source.wx_mini` 置空（避免唯一索引冲突），
     再删除 `source` 这一行。
  5. 给 `target` 签发新 token（复用 `_issue_token`），返回
     `{"code": 200, "data": {"token": ..., "user": target.public_dict()}}`
- 小程序拿到响应后用返回的新 token 覆盖本地存储的旧 token。
- 合并后，`wx_mini` 已经指向 `target` 这一行——之后无论是这次的 token 还是 30 天后过期
  重新 `wx.login()` 静默登录，`mini_login` 按 `wx_mini` 查到的都是 `target`，天然就是
  同一个身份，`requestDesktop.js` 和 `mini_login`/`me` 现有逻辑都不需要改动。

## 小程序前端（en-mini）

`pages/my/my.vue` 顶部新增个人资料区块（在现有词库列表之上）：

- **资料卡片**：头像（`user.avatar` 为空时显示占位图）+ 昵称文本。
  - 点头像：`<button open-type="chooseAvatar" @chooseavatar="...">`，回调拿到临时文件
    路径后 `uni.uploadFile` 到 `POST /auth/avatar`，成功后更新本地 `user.avatar`。
  - 点昵称：切换成 `<input type="nickname" @blur="...">`，失焦提交到 `POST /auth/profile`。
- **账号区块**（在资料卡片下方）：
  - `user.username` 为空 → 显示两个按钮：
    - "设置账号密码"：弹出用户名+密码输入框，提交到 `POST /auth/set-credentials`。
    - "绑定已有桌面账号"：弹出用户名+密码输入框，提交到 `POST /auth/bind-account`；
      成功后用响应里的新 token 覆盖 `en_desktop_token` 本地存储，并重新拉取
      `user`/词库列表。
  - `user.username` 非空 → 显示 "已绑定账号：{username}"，隐藏上述两个按钮。
- 页面 `onShow` 时新增一次 `GET /auth/me` 拉取当前 `user`，驱动上述展示逻辑（当前
  `my.vue` 只请求了 `libraries/list` 和 `libraries/favorites`，未取过用户信息）。

`common/requestDesktop.js` 不需要改动——它已有的"无 token 或 401 时静默登录"逻辑在
绑定完成后依然成立，因为静默登录查到的就是合并后的账号。

## 测试计划

后端（`tests/en_desktop/test_auth.py`，pytest）：
- `set-credentials`：成功；用户名已占用；密码过短；已有 username 时二次调用报错。
- `bind-account`：成功合并（断言目标账号词库数量、收藏数量、`wx_mini` 已过户、源记录
  已删除、返回新 token 可用于后续请求）；用户名密码错误；绑定自己报错；默认库合并去重；
  自建库同名冲突改名过户；收藏同库冲突去重。
- `profile`/`avatar`：昵称更新成功/长度校验；头像上传后 `user.avatar` 为可访问 URL。

前端：手动在小程序开发者工具里过一遍——头像选择上传、昵称编辑、设置账号密码、绑定
已有桌面账号（准备一个已存在的桌面账号验证合并结果）三条路径均可用，且合并后清缓存
重进小程序仍是绑定后的身份。
