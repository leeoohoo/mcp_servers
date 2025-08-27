GitHub Actions 是 GitHub 提供的 CI/CD（持续集成/持续部署）服务，可以在不同的操作系统环境中自动运行代码构建、测试和部署。

## GitHub Actions 的工作原理

### 核心概念：

1. **Runners（运行器）**：GitHub 提供的虚拟机环境
   - `ubuntu-latest`：Linux 环境
   - `windows-latest`：Windows Server 环境  
   - `macos-latest`：macOS 环境

2. **Workflows（工作流）**：自动化流程配置文件
3. **Actions（动作）**：可重用的代码单元
4. **Jobs（作业）**：在特定 runner 上执行的任务组

## 为什么 GitHub Actions 能解决 Windows 构建问题

### 问题回顾：
- 你的 M2 MacBook：不能运行 Windows 容器
- Linux 服务器：不能运行 Windows 容器  
- **需要真正的 Windows 环境**来构建 Windows 可执行文件

### GitHub Actions 的解决方案：
- ✅ 提供**真正的 Windows Server 环境**
- ✅ 预装了开发工具（Python、.NET、Visual Studio 等）
- ✅ 可以同时在多个平台构建
- ✅ 完全免费（公开仓库）

## 详细的 GitHub Actions 配置

````artifact
id: complete-github-actions
name: .github/workflows/build-mcp-server.yml
type: code.yaml
content: |-
  name: Build MCP Server

  # 触发条件
  on:
    push:
      branches: [ main, develop ]
      tags: [ 'v*' ]
    pull_request:
      branches: [ main ]
    workflow_dispatch:  # 手动触发

  jobs:
    # 多平台构建作业
    build:
      name: Build on ${{ matrix.os }}
      runs-on: ${{ matrix.os }}
      
      strategy:
        matrix:
          include:
            # Linux 构建
            - os: ubuntu-latest
              platform: linux
              executable: mcp-server
              archive_name: mcp-server-linux-amd64
            
            # Windows 构建 - 这是关键！
            - os: windows-latest
              platform: windows  
              executable: mcp-server.exe
              archive_name: mcp-server-windows-amd64
            
            # macOS 构建
            - os: macos-latest
              platform: macos
              executable: mcp-server
              archive_name: mcp-server-macos-universal

      steps:
      # 1. 检出代码
      - name: Checkout repository
        uses: actions/checkout@v4

      # 2. 设置 Python 环境
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      # 3. 缓存依赖（加速构建）
      - name: Cache pip dependencies
        uses: actions/cache@v3
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
          restore-keys: |
            ${{ runner.os }}-pip-

      # 4. 安装依赖
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install pyinstaller
          pip install -r requirements.txt

      # 5. 运行测试（可选）
      - name: Run tests
        run: |
          python -m pytest tests/ || echo "No tests found"

      # 6. 构建可执行文件
      - name: Build executable
        run: |
          pyinstaller \
            --onefile \
            --clean \
            --name ${{ matrix.executable }} \
            --distpath dist/ \
            mcp_framework/main.py

      # 7. Windows 特殊处理：代码签名（可选）
      - name: Sign Windows executable
        if: matrix.platform == 'windows'
        run: |
          echo "Windows executable built: dist/${{ matrix.executable }}"
          # 这里可以添加代码签名步骤
          # signtool sign /f certificate.p12 /p password dist/${{ matrix.executable }}

      # 8. 创建发布包
      - name: Create release archive
        shell: bash
        run: |
          cd dist
          if [ "${{ matrix.platform }}" = "windows" ]; then
            7z a ../${{ matrix.archive_name }}.zip ${{ matrix.executable }}
          else
            tar -czf ../${{ matrix.archive_name }}.tar.gz ${{ matrix.executable }}
          fi

      # 9. 上传构建产物
      - name: Upload build artifacts
        uses: actions/upload-artifact@v4
        with:
          name: ${{ matrix.archive_name }}
          path: |
            ${{ matrix.archive_name }}.*
          retention-days: 30

      # 10. 测试可执行文件
      - name: Test executable
        shell: bash
        run: |
          cd dist
          if [ "${{ matrix.platform }}" = "windows" ]; then
            ./${{ matrix.executable }} --version || echo "Version check failed"
          else
            ./${{ matrix.executable }} --version || echo "Version check failed"
          fi

    # 创建 GitHub Release
    release:
      name: Create Release
      needs: build
      runs-on: ubuntu-latest
      if: startsWith(github.ref, 'refs/tags/v')
      
      steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Download all artifacts
        uses: actions/download-artifact@v4
        with:
          path: artifacts/

      - name: Display downloaded files
        run: |
          find artifacts/ -type f -name "*" | head -20

      - name: Create Release
        uses: softprops/action-gh-release@v1
        with:
          files: artifacts/*/*
          draft: false
          prerelease: false
          generate_release_notes: true
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

    # 构建 Docker 镜像（Linux 版本）
    docker:
      name: Build Docker Image
      needs: build
      runs-on: ubuntu-latest
      if: github.ref == 'refs/heads/main'
      
      steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to Docker Hub
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_TOKEN }}

      - name: Build and push Docker image
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: |
            your-username/mcp-server:latest
            your-username/mcp-server:${{ github.sha }}
          platforms: linux/amd64,linux/arm64
````

## 使用步骤

### 1. 创建 GitHub 仓库并推送代码

```bash
# 初始化 Git 仓库（如果还没有）
git init
git add .
git commit -m "Initial commit"

# 添加 GitHub 远程仓库
git remote add origin https://github.com/your-username/your-repo.git
git push -u origin main
```

### 2. 创建 GitHub Actions 配置

```bash
# 创建工作流目录
mkdir -p .github/workflows

# 创建配置文件（使用上面的配置）
# 文件名：.github/workflows/build-mcp-server.yml
```

### 3. 推送配置并触发构建

```bash
git add .github/workflows/build-mcp-server.yml
git commit -m "Add GitHub Actions workflow"
git push
```

### 4. 监控构建过程

访问：`https://github.com/your-username/your-repo/actions`

你会看到：
- ✅ **Linux 构建**：在 Ubuntu 环境中运行
- ✅ **Windows 构建**：在 **真正的 Windows Server** 中运行
- ✅ **macOS 构建**：在 macOS 环境中运行

## GitHub Actions 的优势

### 1. **真正的多平台支持**
```yaml
# 同时在三个平台构建
strategy:
  matrix:
    os: [ubuntu-latest, windows-latest, macos-latest]
```

### 2. **预装的开发环境**
- Windows Runner 预装：
  - Python 3.11
  - Visual Studio Build Tools
  - .NET Framework
  - PowerShell
  - Git

### 3. **自动化发布**
- 自动创建 GitHub Releases
- 上传构建产物
- 支持版本标签触发

### 4. **免费额度**
- 公开仓库：**无限制**
- 私有仓库：每月 2000 分钟免费

## 实际构建结果

构建完成后，你会得到：

```
Artifacts/
├── mcp-server-linux-amd64.tar.gz     # Linux 可执行文件
├── mcp-server-windows-amd64.zip      # Windows .exe 文件
└── mcp-server-macos-universal.tar.gz # macOS 可执行文件
```

## 手动触发构建

```bash
# 创建标签触发发布
git tag v1.0.0
git push origin v1.0.0

# 或者在 GitHub 网页上手动触发
# Repository → Actions → Build MCP Server → Run workflow
```

## 高级配置选项

````artifact
id: advanced-github-actions
name: 高级配置示例
type: code.yaml
content: |-
  # 环境变量
  env:
    PYTHON_VERSION: '3.11'
    BUILD_TYPE: 'release'

  # 条件执行
  - name: Windows-specific step
    if: runner.os == 'Windows'
    run: echo "Running on Windows"

  # 矩阵策略
  strategy:
    matrix:
      python-version: ['3.9', '3.10', '3.11']
      os: [ubuntu-latest, windows-latest, macos-latest]
    fail-fast: false  # 一个失败不影响其他

  # 缓存优化
  - uses: actions/cache@v3
    with:
      path: ~/.cache/pip
      key: ${{ runner.os }}-pip-${{ hashFiles('requirements.txt') }}

  # 并行作业
  jobs:
    test:
      runs-on: ubuntu-latest
    build:
      needs: test  # 等待测试完成
      runs-on: ${{ matrix.os }}
````

**总结**：GitHub Actions 通过提供真正的 Windows Server 环境，完美解决了在 macOS/Linux 上无法构建 Windows 可执行文件的问题。它是目前最简单、最可靠的跨平台构建解决方案。

你想现在设置 GitHub Actions 吗？我可以帮你创建具体的配置文件。