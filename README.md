# EN API - Python 版本

## 数据库

在项目根目录配置 `.env`（或环境变量）：

- **English 库**：`DB_HOST`、`DB_USER`、`DB_PASSWORD`、`DB_DATABASE`（缺省 localhost / english）
- **PDD 库**：`PDD_DB_*`（缺省同主机、库名 `pdd_report`）

`config/db.py` 会在导入时自动加载 `.env`。密码勿写入仓库：复制 `.env.example` 为 `.env` 后本地填写 `DB_PASSWORD`。

## 安装依赖

```bash
pip install -r requirements.txt
```

## 启动

**开发**（带热重载）：

```bash
python main.py
```

**生产**（多 worker，端口可用环境变量 `PORT`，默认 3000）：

```bash
uvicorn app.app:app --host 0.0.0.0 --port ${PORT:-3000} --workers 4
```

或先 `export PORT=3000` 再执行上述命令。
