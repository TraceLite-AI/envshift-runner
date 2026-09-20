// 装置补丁:让 dsh-llm-deepseek 在 DSH_THINKING=off 时不把 thinking / reasoning_effort 放上线。
//
// 为什么不能只改 cordis.yaml:插件 resolveThinking() 里 options.reasoningEffort 由 dsh-agent-default-model /
// dsh-agent-loop 注入默认 effort,配置里两个字段都不写,线上照样是 thinking:{type:enabled}+reasoning_effort:high;
// 配 reasoningEffort:off 又会发 thinking:{type:disabled}。而 OpenAI 兼容网关(computrix)上 GPT 系拒任何 thinking 字段、
// 带 tools 时拒 reasoning_effort,claude-opus-4-8 拒 reasoning_effort ——本地 curl 逐字段坐实(2026-09-20)。
//
// 默认(DSH_THINKING 未设或 on)走原代码路径,请求体与既有 deepseek-flash 结果逐字节相同。
// npm ci 之后运行一次;可重复运行(幂等);锚点找不到就报错退出,绝不静默跳过。
//
// 第二处:流式 tool_calls 增量里空字符串的 function.name 不能覆盖已收到的名字。
// computrix 把 Anthropic 流翻译成 OpenAI 格式时,首个增量带 name:"write",后续增量带 name:""(而不是省略字段);
// 原代码 `!== void 0` 就把名字覆盖成空串 → 工具找不到("unknown tool")→ 下一轮请求体带空名工具调用被 400。
// DeepSeek 官网从不发空名增量,这条对官网路径无行为差异。
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

// ★Windows 上 new URL(...).pathname 是 '/D:/a/...',再 path.join 会拼成 'D:\D:\a\...'(冒烟一次坐实);用 fileURLToPath
const here = path.dirname(fileURLToPath(import.meta.url))
const target = path.join(here, 'node_modules/@deepseek-ai/dsh-llm-deepseek/lib/index.js')
const PATCHES = [
  {
    anchor: 'const resolvedThinking = resolveThinking(options, defaults);',
    patched: 'const resolvedThinking = process.env.DSH_THINKING === "off" ? {} : resolveThinking(options, defaults); /* envshift patch_llm:thinking */',
  },
  {
    anchor: 'if (call.function?.name !== void 0) block.name = call.function.name;',
    patched: 'if (call.function?.name) block.name = call.function.name; /* envshift patch_llm:empty-name */',
  },
]

let src = fs.readFileSync(target, 'utf8')
for (const { anchor, patched } of PATCHES) {
  if (src.includes(patched)) {
    console.log('patch_llm: already applied — ' + patched.split('/* ')[1])
  } else if (src.includes(anchor)) {
    src = src.replace(anchor, patched)
    console.log('patch_llm: applied — ' + patched.split('/* ')[1])
  } else {
    console.error('patch_llm: anchor not found in ' + target + ': ' + anchor + ' — plugin version changed, refusing to continue')
    process.exit(2)
  }
}
fs.writeFileSync(target, src)
