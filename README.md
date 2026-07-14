## 数据库
在项目根目录配置 `.env`（或环境变量）：

- **English 库**：`DB_HOST`、`DB_USER`、`DB_PASSWORD`、`DB_DATABASE`（缺省 localhost / english）
- **PDD 库**：`PDD_DB_*`（缺省同主机、库名 `pdd_report`）

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

先 `fuser -k` 释放端口上的旧进程，再以 `nohup` 后台启动 uvicorn，日志输出到项目根目录的 `nohup.out`：

```bash
./start.sh
```
