"use strict";
(() => {
  const db = window.MMD_LIBRARY;
  if (!db) {
    document.getElementById("main").textContent = "资料数据尚未构建。请按仓库说明运行 build_gallery.py，再打开交付目录的 index.html。";
    return;
  }
  const $ = (selector, scope = document) => scope.querySelector(selector);
  const $$ = (selector, scope = document) => [...scope.querySelectorAll(selector)];
  const esc = value => String(value ?? "").replace(/[&<>"']/g, char => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]));
  const icon = name => `<svg aria-hidden="true"><use href="#i-${name}"/></svg>`;
  const byId = new Map(db.entries.map(entry => [entry.id, entry]));
  const downloads = new Map(db.components.map(item => [item.download, { content: JSON.stringify(item.data, null, 2), type: "application/json" }]));
  Object.values(db.documents).forEach(doc => downloads.set(doc.source, { content: doc.text, type: "text/markdown;charset=utf-8" }));
  const aspect = { landscape: "16:9 横屏", portrait: "9:16 竖屏", square: "1:1 实验" };
  const storage = {
    get(key, fallback) { try { return JSON.parse(localStorage.getItem(key)) ?? fallback; } catch { return fallback; } },
    set(key, value) { try { localStorage.setItem(key, JSON.stringify(value)); return true; } catch { return false; } }
  };
  const saved = storage.get("frame-atelier:favorites:v1", []);
  const favorites = new Set(Array.isArray(saved) ? saved.filter(id => byId.has(id)) : []);
  const selected = new Set();
  const state = { view: "gallery", category: "all", family: "all", aspect: "all", status: "all", query: "" };
  let currentEntry = null;
  let toastTimer;
  const theme = storage.get("frame-atelier:theme:v1", "dark");
  document.documentElement.dataset.theme = theme === "light" ? "light" : "dark";

  function toast(message) {
    clearTimeout(toastTimer);
    $("#toast").textContent = message;
    $("#toast").classList.add("show");
    toastTimer = setTimeout(() => $("#toast").classList.remove("show"), 2700);
  }
  function status(entry) {
    return `<span class="status" data-state="${esc(entry.status)}">${esc(db.statuses[entry.status])}</span>`;
  }
  function heading(eyebrow, title, description, actions = "") {
    return `<div class="page-intro"><div class="eyebrow">${esc(eyebrow)}</div><h1>${esc(title)}</h1><p>${esc(description)}</p>${actions ? `<div class="actions">${actions}</div>` : ""}</div>`;
  }
  function parameter(item) {
    return `<details class="parameter"><summary>${esc(item.path)}</summary><pre><code>${esc(JSON.stringify(item.data, null, 2))}</code></pre><a href="${esc(item.download)}" download>下载这个 JSON ↗</a></details>`;
  }
  function docLink(name) {
    return `<a class="doc-link" href="#learn/${encodeURIComponent(name)}"><span>${esc(db.documents[name]?.title || name)}</span><span>↗</span></a>`;
  }
  function card(entry) {
    const liked = favorites.has(entry.id);
    const picked = selected.has(entry.id);
    return `<article class="preset-card" data-id="${esc(entry.id)}">
      <div class="card-media">
        ${entry.aspect !== "landscape" ? `<img class="blur-back" src="${esc(entry.image.src)}" alt="" loading="lazy" aria-hidden="true">` : ""}
        <button class="card-image-button" data-open="${esc(entry.id)}" aria-label="查看${esc(entry.title)}"><img src="${esc(entry.image.src)}" alt="${esc(entry.title)}实际渲染预览" loading="lazy" width="${entry.image.width}" height="${entry.image.height}"></button>
        <div class="card-topline"><span class="aspect-badge">${aspect[entry.aspect]}</span><button class="favorite-button ${liked ? "saved" : ""}" data-favorite="${esc(entry.id)}" aria-label="${liked ? "取消收藏" : "收藏"}${esc(entry.title)}" aria-pressed="${liked}">${icon("star")}</button></div>
        <span class="card-play">${icon(entry.video ? "play" : "layers")}${entry.video ? `${entry.duration}s · ${entry.fps} FPS` : "静帧研究"}</span>
      </div>
      <div class="card-body"><div class="card-collection">${esc(entry.collection)}</div><div class="card-title"><button data-open="${esc(entry.id)}">${esc(entry.title)}</button><span>↗</span></div><p class="card-description">${esc(entry.subtitle)}</p><div class="card-footer"><div>${status(entry)}${entry.adopted ? '<span class="adopted-tag">当前基线</span>' : ""}</div><button class="compare-toggle ${picked ? "selected" : ""}" data-compare="${esc(entry.id)}" aria-pressed="${picked}">${icon(picked ? "check" : "compare")}${picked ? "已选对照" : "加入对照"}</button></div></div>
    </article>`;
  }
  function matches(entry) {
    const query = state.query.toLocaleLowerCase();
    const haystack = [entry.title, entry.subtitle, entry.collection, db.categories[entry.category], db.families[entry.family], ...entry.look].join(" ").toLocaleLowerCase();
    return (state.category === "all" || entry.category === state.category) &&
      (state.family === "all" || entry.family === state.family) &&
      (state.aspect === "all" || entry.aspect === state.aspect) &&
      (state.status === "all" || entry.status === state.status) && (!query || haystack.includes(query)) &&
      (state.view !== "favorites" || favorites.has(entry.id));
  }
  function renderGallery() {
    const isFavorites = state.view === "favorites";
    $("#gallery-title").innerHTML = `${isFavorites ? "我的收藏" : "预设画廊"} <span id="entry-count">${isFavorites ? favorites.size : db.entries.length}</span>`;
    $("#gallery-subtitle").innerHTML = isFavorites
      ? '<span class="favorite-actions"><button class="text-button" data-export-favorites>导出收藏</button><button class="text-button" data-import-favorites>导入收藏</button></span>'
      : "先看效果，再选择你的制作方向。";
    const tabs = [["all", "全部预设"], ...Object.entries(db.categories)];
    $("#category-tabs").innerHTML = tabs.map(([id, label]) => `<button data-category="${id}" class="${state.category === id ? "active" : ""}" aria-pressed="${state.category === id}">${esc(label)}<span>${db.entries.filter(e => (id === "all" || e.category === id) && (!isFavorites || favorites.has(e.id))).length}</span></button>`).join("");
    const filtered = db.entries.filter(matches);
    $("#preset-grid").innerHTML = filtered.map(card).join("");
    $("#empty-state").hidden = filtered.length > 0;
    $("#result-summary").textContent = `显示 ${filtered.length} 项${state.family !== "all" ? " · " + db.families[state.family] : ""}${isFavorites ? " · 收藏仅保存在当前浏览器" : ""}`;
    $("#family-filter").value = state.family;
    $("#aspect-filter").value = state.aspect;
    $("#status-filter").value = state.status;
    $("#nav-favorites").textContent = favorites.size;
  }
  function reset() {
    Object.assign(state, { category: "all", family: "all", aspect: "all", status: "all", query: "" });
    $("#search").value = "";
    $("#hero").hidden = state.view !== "gallery";
    renderGallery();
  }
  function updateTray() {
    $("#compare-tray").hidden = selected.size === 0;
    $("#compare-tray-label").textContent = `已选 ${selected.size} / 2 项`;
    $("#compare-tray-thumbs").innerHTML = [...selected].map(id => `<img src="${esc(byId.get(id).image.src)}" alt="${esc(byId.get(id).title)}">`).join("");
    $("#open-compare").disabled = selected.size !== 2;
  }
  function toggleCompare(id) {
    if (selected.has(id)) selected.delete(id);
    else if (selected.size < 2) selected.add(id);
    else { toast("已选满两项，先取消一项再选择。"); return; }
    if (["gallery", "favorites"].includes(state.view)) renderGallery();
    updateTray();
  }
  function openEntry(id) {
    const entry = byId.get(id);
    if (!entry) { toast("没有找到这项预设。"); return; }
    currentEntry = entry;
    const links = entry.docs.map(docLink).join("");
    const commands = entry.command ? `<div class="command-box"><pre>${esc(entry.command)}</pre><button class="button" data-copy-command>${icon("copy")}复制复现命令</button><p>在仓库根目录运行，输出路径需使用全新目录。</p></div>` : "";
    $("#detail-content").innerHTML = `<div class="detail-layout"><div class="detail-visual"><img class="detail-image" src="${esc(entry.image.src)}" alt="${esc(entry.title)}完整画幅预览">${entry.video ? `<video class="detail-video" controls playsinline preload="none" poster="${esc(entry.image.src)}" hidden><source src="${esc(entry.video)}" type="video/mp4"></video><div class="media-tabs"><button class="active" data-media="image">静帧</button><button data-media="video">${icon("play")} 播放样片</button>${entry.diagnostic_video ? `<button data-media="diagnostic">${esc(entry.diagnostic_label || "稳定性测试 · 3s")}</button>` : ""}</div>` : '<div class="media-tabs"><span class="chip">已验证范围：静帧</span></div>'}</div><div class="detail-info"><div class="eyebrow">${esc(entry.collection)}</div><h2>${esc(entry.title)}</h2><p>${esc(entry.subtitle)}</p><div class="detail-meta">${status(entry)}<span class="chip">${aspect[entry.aspect]}</span>${entry.adopted ? '<span class="chip">当前认可基线</span>' : ""}</div><div class="look-tags">${entry.look.map(text => `<span class="chip">${esc(text)}</span>`).join("")}</div><div class="detail-section"><h3>适用条件</h3><p>${esc(entry.compatibility)}</p><h3>实际验证</h3><ul>${entry.evidence.map(text => `<li>${esc(text)}</li>`).join("")}</ul></div><div class="detail-section limits"><h3>使用前看这里</h3><ul>${entry.limits.map(text => `<li>${esc(text)}</li>`).join("")}</ul></div><div class="detail-actions"><button class="button" data-favorite="${esc(id)}">${icon("star")}${favorites.has(id) ? "已收藏 · 取消" : "收藏预设"}</button><button class="button" data-copy-project>${icon("copy")}复制工程路径</button><button class="button" data-compare="${esc(id)}">${icon("compare")}加入／取消对照</button></div><div class="detail-section"><h3>方法与学习笔记</h3>${links}</div><div class="detail-section"><h3>参数与复用</h3><p>参数文件可以下载；项目配方仍需对应模型与源工程。</p>${entry.parameters.map(parameter).join("")}${commands}</div></div></div>`;
    const dialog = $("#detail-dialog");
    if (!dialog.open) dialog.showModal();
    history.replaceState(null, "", `#preset/${encodeURIComponent(id)}`);
    $(".detail-info").scrollTop = 0;
  }
  function openSelectedComparison() {
    if (selected.size !== 2) return;
    const items = [...selected].map(id => byId.get(id));
    $("#compare-content").innerHTML = `<h2>并排看，差别更清楚。</h2><p>保留完整画幅。不同内容的预设用于观察风格，不能当作同姿态的受控实验。</p><div class="side-by-side">${items.map(entry => `<figure><img src="${esc(entry.image.src)}" alt="${esc(entry.title)}完整画幅"><figcaption>${esc(entry.title)}</figcaption><small>${aspect[entry.aspect]} · ${esc(db.statuses[entry.status])} · ${esc(entry.compatibility)}</small></figure>`).join("")}</div>`;
    $("#compare-dialog").showModal();
  }
  function renderStudies() {
    const query = state.query.toLocaleLowerCase();
    $("#compare-view").innerHTML = heading("CONTROLLED STUDIES", "把变化，看得更清楚。", "这里保存同一研究场景中的受控对照。拖动分界线，或用键盘左右键调整；也可以在画廊选择任意两项并排查看。") + db.comparisons.filter(pair => `${pair.title} ${pair.subtitle}`.toLocaleLowerCase().includes(query)).map(pair => `<section class="compare-study"><h2>${esc(pair.title)}</h2><p>${esc(pair.subtitle)}</p><div class="image-comparison ${pair.before.width === pair.before.height ? "square" : ""}" style="aspect-ratio:${pair.before.width}/${pair.before.height};--position:50%"><img src="${esc(pair.before.src)}" alt="${esc(pair.before_label)}"><img class="comparison-after" src="${esc(pair.after.src)}" alt="${esc(pair.after_label)}"><div class="compare-labels"><span>${esc(pair.before_label)}</span><span>${esc(pair.after_label)}</span></div><div class="slider-line"></div><input type="range" min="0" max="100" value="50" aria-label="${esc(pair.title)}分界位置"></div><a href="#learn/${pair.doc}">阅读这次实验的方法与边界 ↗</a></section>`).join("");
  }
  function renderKnowledge() {
    const query = state.query.toLocaleLowerCase();
    const groups = db.knowledge_groups.map(group => ({ ...group, docs: group.docs.filter(name => `${group.title} ${db.documents[name].title} ${db.documents[name].text}`.toLocaleLowerCase().includes(query)) })).filter(group => group.docs.length);
    $("#knowledge-view").innerHTML = heading("KNOWLEDGE MAP", "把学过的，连成地图。", `${Object.keys(db.documents).length} 篇笔记按制作问题归类。文中历史状态保留日期，当前项目以预设详情与最新验收记录为准。`) + `<div class="knowledge-grid">${groups.map(group => `<section class="knowledge-group"><div class="group-top"><h2>${esc(group.title)}</h2><span>${group.docs.length} 篇</span></div><p>${esc(group.description)}</p>${group.docs.map(name => `<a href="#learn/${encodeURIComponent(name)}"><span class="doc-name">${esc(db.documents[name].title)}</span><span>↗</span></a>`).join("")}</section>`).join("")}</div>${groups.length ? "" : '<div class="empty-state"><h3>没有找到相关笔记</h3><p>试试更简短的关键词。</p></div>'}`;
  }
  function renderComponents() {
    const query = state.query.toLocaleLowerCase();
    const names = { styles: "风格模块", stages: "舞台灯光", quality: "材质实验", typography: "字幕布局", projects: "制作项目", recipes: "工程配方" };
    const filtered = db.components.filter(item => `${item.path} ${item.id} ${JSON.stringify(item.data)}`.toLocaleLowerCase().includes(query));
    $("#components-view").innerHTML = heading("PARAMETER COMPONENTS", "一套风格，也可以拆开复用。", `共 ${db.components.length} 份 JSON。渲染、后期、布局、灯光与工程配方分别保存；单个组件可用，不代表新组合已经验收。`) + `<p class="result-line">显示 ${filtered.length} 项 · 这里展示文件本身，验证范围以关联预设为准。</p><div class="component-table">${filtered.map(item => `<div class="component-row"><div><strong>${esc(item.id)}</strong><small>${esc(item.path)}</small></div><span class="chip">${esc(names[item.path.split("/")[1]] || "组件")}</span><a href="${esc(item.download)}" download>下载 ↗</a>${parameter(item)}</div>`).join("")}</div>`;
  }
  function renderRoadmap() {
    const query = state.query.toLocaleLowerCase();
    $("#roadmap-view").innerHTML = heading("THE NEXT FRAME", "接下来，质感往哪里走。", "我认为最值得加强的是受光与空间关系、动态稳定性和分层合成。先把已有画面做稳，再用版本化预设发展猪猪自己的风格。") + `<div class="roadmap-list">${db.roadmap.filter(item => `${item.title} ${item.description} ${item.evidence} ${item.acceptance}`.toLocaleLowerCase().includes(query)).map(item => `<section class="roadmap-item"><div class="road-number">${item.number}</div><div><span class="chip">${esc(item.priority)}</span><h2>${esc(item.title)}</h2><p>${esc(item.description)}</p><div class="road-evidence"><div><strong>当前依据</strong>${esc(item.evidence)}</div><div><strong>怎样算做好</strong>${esc(item.acceptance)}</div></div><a href="#learn/${item.doc}">查看对应笔记 ↗</a></div></section>`).join("")}</div>`;
  }
  function renderReader(name) {
    const doc = db.documents[name];
    if (!doc) {
      $("#reader-view").innerHTML = heading("DOCUMENT", "这篇笔记暂未收录", "可以从知识地图查找现有内容。", '<a class="button" href="#knowledge">返回知识地图</a>');
      return;
    }
    $("#reader-view").innerHTML = `<div class="reader-top"><a href="#knowledge">← 返回知识地图</a><a href="${esc(doc.source)}" download>下载 Markdown ↗</a></div><div class="reader-layout"><div class="reader-paper"><article>${doc.html}</article></div><nav class="reader-toc" aria-label="文档目录"><p>本页目录</p><div id="reader-toc-links"></div></nav></div>`;
    const headings = $$("article h2,article h3", $("#reader-view"));
    $("#reader-toc-links").innerHTML = headings.map((node, index) => {
      node.id = `doc-section-${index}`;
      return `<a href="#" data-scroll-target="${node.id}">${esc(node.textContent)}</a>`;
    }).join("");
    $("#breadcrumb").textContent = "知识地图 / " + doc.title;
  }
  function route() {
    let parts;
    try { parts = decodeURIComponent(location.hash.slice(1) || "gallery").split("/"); } catch { parts = ["gallery"]; }
    let view = parts[0];
    const preset = view === "preset" ? parts[1] : null;
    if (preset) view = "gallery";
    if (!["gallery", "favorites", "compare", "knowledge", "components", "roadmap", "learn"].includes(view)) view = "gallery";
    const changed = state.view !== view;
    state.view = view;
    $$('dialog[open]').forEach(dialog => dialog.close());
    $$("main>.view").forEach(section => { section.hidden = true; });
    $("#hero").hidden = view !== "gallery" || state.query !== "" || state.family !== "all";
    $$("[data-nav]").forEach(link => link.classList.toggle("active", link.dataset.nav === (view === "learn" ? "knowledge" : view)));
    const titles = { gallery: "预设画廊", favorites: "我的收藏", compare: "效果对照", knowledge: "知识地图", components: "参数组件", roadmap: "下一步提升", learn: "知识地图" };
    $("#breadcrumb").textContent = titles[view];
    $("#search").placeholder = ["knowledge", "learn"].includes(view) ? "搜索所有笔记内容…" : view === "components" ? "搜索组件与参数…" : "搜索风格、技法或笔记…";
    const section = $("#" + (view === "favorites" ? "gallery" : view === "learn" ? "reader" : view) + "-view");
    section.hidden = false;
    if (["gallery", "favorites"].includes(view)) renderGallery();
    if (view === "compare") renderStudies();
    if (view === "knowledge") renderKnowledge();
    if (view === "components") renderComponents();
    if (view === "roadmap") renderRoadmap();
    if (view === "learn") renderReader(parts[1]);
    if (changed) window.scrollTo({ top: 0, behavior: "instant" });
    if (preset) openEntry(preset);
  }
  async function copy(text) {
    try {
      if (!navigator.clipboard?.writeText) throw new Error("Clipboard unavailable");
      await navigator.clipboard.writeText(text);
      toast("已复制。");
    } catch {
      $("#copy-text").value = text;
      $("#copy-dialog").showModal();
      $("#copy-text").focus();
      $("#copy-text").select();
    }
  }
  function saveFavorites() {
    if (!storage.set("frame-atelier:favorites:v1", [...favorites])) toast("本次收藏已保留；可导出 JSON 保存。");
    $("#nav-favorites").textContent = favorites.size;
  }
  function downloadText(content, filename, type) {
    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    document.body.append(anchor);
    anchor.click();
    anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  function exportFavorites() {
    downloadText(JSON.stringify({ schema_version: 1, favorites: [...favorites] }, null, 2), "frame-atelier-favorites.json", "application/json");
  }
  function themeLabel() {
    $("#theme-toggle").setAttribute("aria-label", document.documentElement.dataset.theme === "dark" ? "切换浅色主题" : "切换深色主题");
  }
  $("#family-filter").innerHTML = '<option value="all">全部风格</option>' + Object.entries(db.families).map(([id, text]) => `<option value="${id}">${esc(text)}</option>`).join("");
  $("#status-filter").innerHTML = '<option value="all">全部状态</option>' + Object.entries(db.statuses).map(([id, text]) => `<option value="${id}">${esc(text)}</option>`).join("");
  $("#nav-total").textContent = db.entries.length;
  $("#hero-entry-count").textContent = `${db.entries.length} 项预设`;
  $("#hero-doc-count").textContent = `${Object.keys(db.documents).length} 篇笔记`;
  themeLabel();
  document.addEventListener("click", event => {
    const button = event.target.closest("button,a");
    if (!button) return;
    if (button.hasAttribute("download")) {
      const path = button.getAttribute("href");
      const file = downloads.get(path);
      if (file) {
        event.preventDefault();
        downloadText(file.content, path.split("/").pop(), file.type);
      }
    }
    if (button.matches("[data-close]")) button.closest("dialog").close();
    if (button.dataset.open) openEntry(button.dataset.open);
    if (button.dataset.favorite) {
      const id = button.dataset.favorite;
      if (favorites.has(id)) favorites.delete(id); else favorites.add(id);
      saveFavorites();
      if (["gallery", "favorites"].includes(state.view)) renderGallery();
      if (button.closest(".detail-info")) button.innerHTML = `${icon("star")}${favorites.has(id) ? "已收藏 · 取消" : "收藏预设"}`;
    }
    if (button.dataset.compare) toggleCompare(button.dataset.compare);
    if (button.dataset.category) { state.category = button.dataset.category; renderGallery(); }
    if (button.dataset.family) {
      Object.assign(state, { category: "all", family: button.dataset.family, aspect: "all", status: "all", query: "" });
      $("#search").value = "";
      if (location.hash !== "#gallery") location.hash = "gallery"; else route();
      $("#gallery-heading").scrollIntoView({ block: "start" });
    }
    if (button.dataset.media) {
      const video = $(".detail-video");
      const isVideo = button.dataset.media !== "image";
      $(".detail-image").hidden = isVideo;
      video.hidden = !isVideo;
      $$("[data-media]").forEach(tab => tab.classList.toggle("active", tab === button));
      if (isVideo) {
        const target = button.dataset.media === "diagnostic" ? currentEntry.diagnostic_video : currentEntry.video;
        if (video.getAttribute("src") !== target) { video.src = target; video.load(); }
        video.play().catch(() => toast("请点击播放器的播放按钮。"));
      } else video.pause();
    }
    if (button.hasAttribute("data-copy-command")) copy(currentEntry.command);
    if (button.hasAttribute("data-copy-project")) copy(currentEntry.project.replaceAll("/", "\\"));
    if (button.hasAttribute("data-export-favorites")) exportFavorites();
    if (button.hasAttribute("data-import-favorites")) $("#favorites-file").click();
    if (button.dataset.scrollTarget) {
      event.preventDefault();
      document.getElementById(button.dataset.scrollTarget).scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start" });
    }
  });
  ["family", "aspect", "status"].forEach(key => $("#" + key + "-filter").addEventListener("change", event => {
    state[key] = event.target.value;
    $("#hero").hidden = state.view !== "gallery" || state.query !== "" || state.family !== "all";
    renderGallery();
  }));
  $("#reset-filters").addEventListener("click", reset);
  $("#empty-reset").addEventListener("click", reset);
  $("#search").addEventListener("input", event => {
    state.query = event.target.value.trim();
    if (state.view === "learn") { location.hash = "knowledge"; return; }
    route();
  });
  $("#explore").addEventListener("click", () => $("#gallery-heading").scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" }));
  $("#clear-compare").addEventListener("click", () => { selected.clear(); updateTray(); if (["gallery", "favorites"].includes(state.view)) renderGallery(); });
  $("#open-compare").addEventListener("click", openSelectedComparison);
  $("#theme-toggle").addEventListener("click", () => {
    document.documentElement.dataset.theme = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    storage.set("frame-atelier:theme:v1", document.documentElement.dataset.theme);
    themeLabel();
  });
  document.addEventListener("input", event => {
    if (event.target.matches('.image-comparison input[type="range"]')) event.target.parentElement.style.setProperty("--position", `${event.target.value}%`);
  });
  $("#favorites-file").addEventListener("change", async event => {
    const file = event.target.files[0];
    if (!file) return;
    try {
      if (file.size > 1024 * 1024) throw new Error("File too large");
      const data = JSON.parse(await file.text());
      if (data.schema_version !== 1 || !Array.isArray(data.favorites)) throw new Error("Invalid format");
      const recognized = data.favorites.filter(id => typeof id === "string" && byId.has(id));
      recognized.forEach(id => favorites.add(id));
      saveFavorites();
      renderGallery();
      toast(`已合并 ${new Set(recognized).size} 项收藏。`);
    } catch { toast("未能导入，请选择本站导出的收藏 JSON。"); }
    event.target.value = "";
  });
  $$('dialog').forEach(dialog => {
    dialog.addEventListener("close", () => {
      $$("video", dialog).forEach(video => video.pause());
      if (dialog.id === "detail-dialog" && location.hash.startsWith("#preset/")) history.replaceState(null, "", "#gallery");
    });
    dialog.addEventListener("click", event => { if (event.target === dialog) {
      const rect = dialog.getBoundingClientRect();
      if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) dialog.close();
    } });
  });
  document.addEventListener("keydown", event => {
    if (event.key === "/" && !event.target.closest("input,textarea,select,[contenteditable=true]") && !$('dialog[open]')) { event.preventDefault(); $("#search").focus(); }
  });
  window.addEventListener("hashchange", route);
  route();
})();
