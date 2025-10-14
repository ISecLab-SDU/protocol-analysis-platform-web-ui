# 开发说明

## 技术栈

（当前仓库已经过删裁）

1. 语言：TypeScript

   可以简单理解为强类型的 JavaScript。

2. 核心 JavaScript UI 框架：Vue 3

   与之相对应的“竞品”是 Angular 和 React，它们负责为开发 HTML + CSS + JavaScript 应用时遇到的一系列常见问题提供系统性解决方案。同时，它们自身会约定很多概念和用法，开源社区也会在它们的基础上扩展生态系统，使得熟练使用它们本身也成为一种需要学习的技术。

3. UI 组件设计框架：Ant Design Vue

   简单理解就是美工。看到的各种漂亮的控件都是由这个框架提供的。

4. 脚手架与构建工具：Vite

   Vue 3 官方搭配，负责打包和依赖管理，我们的项目当中不用和它打太多交道。

5. Mock 后端：Nitro

   一个伪造（Mock）的后端，基于 Nitro（一个轻量级的 JavaScript 服务器引擎）开发。方便在不接入后端服务器的情况下测试前端业务的正确性。**原则上，编写的代码最好从一开始就实现前后端的分离，测试用的伪造数据应该由 Mock 后端提供，但是不强求。**

## 环境配置

如有条件，推荐在 Linux 下配置，很方便。Windows 亦可，但是根据个人经验比 Linux 不确定性更多。

.6 服务器上已经有了 Node.js 环境，但是受限于防火墙可能不方便，这个过几天可以调整一下。

```
sudo apt update
sudo apt install npm
npm i -g corepack
pnpm install
pnpm dev
```

## 需要修改的地方

现有的一些修改也是 Vibe Coding 的产物。如果你使用的 Agent 足够智能，单纯地审阅前几次 commit 的结果应该足以让它做出合适的更改。如果它做不到，你可能需要阅读以下文本，向它说明需要在哪些地方做修改。

### 前端部分

#### 第一步：识别路由

简单来说，就是先识别你写出来的东西要通过哪个网址才可以访问。

相关文件在 `apps/web-antd/src/router/routes/modules` 下。我们以协议合规性分析（`protocol-compliance.ts`）为例：

```
{
    name: 'ProtocolComplianceExtract',
    path: '/protocol-compliance/extract',
    component: () =>
    import('#/views/protocol-compliance/extract/index.vue'),
    meta: {
    	title: '协议规则提取',
    },
},
```

注意 `path` 字段，我通过以下路径来访问我本地的部署：

```
http://192.168.31.236:5666/protocol-compliance/extract
```

同时，注意 `component` 字段，它对应于你编写的 Vue 文件位置：

```
apps/web-antd/src/views/protocol-compliance/extract/index.vue
```

#### 第二步：编写前端

根据路由信息判断出你需要编写的文件位置，剩下的交给 AI。Vue 3 不是一个能速成的框架。

注意，如果你打算使用 Mock 后端的话请把 API 交互和 `.vue` 文件分离，并记住你设定的 API 基地址。

### 后端部分（假设你也使用 Mock 后端而非硬布线）

基本流程亦同，只是需要注意 Nitro 使用的是基于文件的路由。

同样以 `protocol-compliance.ts` 为例，它所使用的 API 接口由 `apps/web-antd/src/api/protocol-compliance.ts` 定义，基地址为：

```
/protocol-compliance/tasks
```

那么，在 Nitro 驱动的 Mock 后端当中，就应该在以下路径编写文件：

```
apps/backend-mock/api/protocol-compliance/tasks.get.ts
apps/backend-mock/api/protocol-compliance/tasks.post.ts
```

同样地，剩下的具体后端逻辑建议 AI 生成。

## Vibe Coding 示例

以下是编写第一个页面所使用的 Prompt（机翻成英文）。还需要几次小调整，效果尚可。使用的 Vibe Coding 工具是 OpenAI Codex，这方面因个人习惯而异。

同一文件夹下的 `AGENTS.md` 是 OpenAI Codex 自动生成的仓库说明，可以被 Codex 或 GitHub Copilot 自动解析。其它 Vibe Coding 工具也可以参考。

```
我们准备来构建我们第一个实质性页面。

<general-idea>
我们现在在构建前端 Web UI 应用，但是时间仓促，我们暂时无法实现后端，所以需要给 mock 后端留出足够的接口。
</general-idea>

<route>
它应该接入到 `apps/web-antd/src/router/routes/modules/protocol-compliance.ts` 所对应的第一个路由项（“协议规则提取”），并作为一个 component 显示在这个 Vue 应用的主体部分。
</route>

<function>
它的输入是一个文档，一般这个文档来自于 RFC 或者其他协议规范。我们应该允许用户上传。
它的输出是一个 JSON 文件。我们允许用户下载。
</function>

<layout>
页面的主体部分是一个代表任务队列的有序列表。有序列表当中的每一个条目都代表用户上传的一个协议规范文档。条目自身应当记录协议文档当前的解析状态。当解析完成之后，会显示可以下载解析结果（JSON 文件）。
当然，这个有序列表需要一个创建新任务的 button 以及与之相配套的边缘情况处理（例如 modal 等）。
</layout>

<tips>
阅读仓库当中已有的代码，尽量复用现成的 UI 组件。
</tips>

```
