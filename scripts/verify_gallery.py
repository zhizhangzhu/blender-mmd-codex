"""Exercise the delivered gallery through a fresh, headless system Chrome."""

import argparse
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--chrome", default="C:/Program Files/Google/Chrome/Application/chrome.exe"
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    checks = []
    errors = []
    requests = []
    report = {"checks": checks, "errors": errors, "remote_requests": requests}
    url = (args.site.resolve() / "index.html").as_uri()
    try:
        with sync_playwright() as runtime:
            browser = runtime.chromium.launch(
                executable_path=args.chrome, headless=True, args=["--mute-audio"]
            )
            context = browser.new_context(
                viewport={"width": 1440, "height": 1100}, accept_downloads=True
            )
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on(
                "console",
                lambda message: (
                    errors.append(message.text) if message.type == "error" else None
                ),
            )
            page.on(
                "request",
                lambda request: (
                    requests.append(request.url)
                    if request.url.startswith(("https://", "http://"))
                    else None
                ),
            )
            page.goto(url, wait_until="load")
            total = page.evaluate("window.MMD_LIBRARY.entries.length")
            expect(page.locator(".preset-card")).to_have_count(total)
            expect(page.locator(".hero-feature>img")).to_have_js_property(
                "complete", True
            )
            assert page.locator(".hero-feature>img").evaluate("e=>e.naturalWidth") > 0
            page.screenshot(path=str(args.output_dir / "desktop-dark.png"))
            checks.append("file:// direct open, catalog and real hero image")
            media = page.evaluate("""async () => {
              const entries=window.MMD_LIBRARY.entries.filter(e=>e.video);
              return await Promise.all(entries.map(entry=>new Promise((resolve,reject)=>{
                const video=document.createElement('video');
                const timer=setTimeout(()=>reject(new Error('Metadata timeout: '+entry.id)),15000);
                video.preload='metadata';
                video.onloadedmetadata=()=>{
                  clearTimeout(timer);
                  resolve({id:entry.id,duration:video.duration,expected:entry.duration,width:video.videoWidth,height:video.videoHeight});
                  video.removeAttribute('src');video.load();
                };
                video.onerror=()=>{clearTimeout(timer);reject(new Error('Unreadable video: '+entry.id));};
                video.src=entry.video;
              })));
            }""")
            assert all(
                abs(item["duration"] - item["expected"]) < 0.15 for item in media
            ), media
            assert all(item["width"] > 0 and item["height"] > 0 for item in media), (
                media
            )
            report["all_video_metadata"] = media
            checks.append(
                "all packaged short videos decode metadata and match duration labels"
            )

            page.get_by_role("button", name="灯光与舞台", exact=False).click()
            stage_count = page.evaluate(
                "window.MMD_LIBRARY.entries.filter(e=>e.category==='stage').length"
            )
            expect(page.locator(".preset-card")).to_have_count(stage_count)
            page.locator("#family-filter").select_option("wuwa")
            expect(page.locator("#empty-state")).to_be_visible()
            page.locator("#empty-reset").click()
            expect(page.locator(".preset-card")).to_have_count(total)
            page.locator("#aspect-filter").select_option("portrait")
            assert page.locator(".preset-card").count() > 0
            assert all(
                "竖屏" in text
                for text in page.locator(".aspect-badge").all_text_contents()
            )
            page.locator("#reset-filters").click()
            page.locator("#search").fill("<img src=x onerror=alert(1)>")
            expect(page.locator("#empty-state")).to_be_visible()
            expect(page.locator("#main img[src=x]")).to_have_count(0)
            page.locator("#empty-reset").click()
            checks.append(
                "combined category/family/aspect filters, empty/reset, escaped search"
            )

            first_id = "genshin-duet-hall-v3"
            page.locator(f'.favorite-button[data-favorite="{first_id}"]').click()
            page.reload(wait_until="load")
            expect(page.locator("#nav-favorites")).to_have_text("1")
            page.locator('[data-nav="favorites"]').click()
            expect(page.locator(".preset-card")).to_have_count(1)
            with page.expect_download() as download_info:
                page.locator("[data-export-favorites]").click()
            download = download_info.value
            downloaded = args.output_dir / "favorites-export.json"
            download.save_as(str(downloaded))
            assert json.loads(downloaded.read_text())["favorites"] == [first_id]
            imported = args.output_dir / "favorites-import.json"
            imported.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "favorites": ["moonlit-vows-v1", "not-a-preset"],
                    }
                ),
                encoding="utf-8",
            )
            page.locator("#favorites-file").set_input_files(str(imported))
            expect(page.locator(".preset-card")).to_have_count(2)
            checks.append(
                "favorites persist on reload; export download and validated import merge"
            )

            if page.evaluate(
                "window.MMD_LIBRARY.entries.some(e=>e.id==='duet-character-layers-v1')"
            ):
                page.goto(url + "#preset/duet-character-layers-v1", wait_until="load")
                expect(page.locator(".detail-info h2")).to_have_text(
                    "映光 · 人物材质分层"
                )
                for kind in ("video", "diagnostic"):
                    page.locator(f'[data-media="{kind}"]').click()
                    page.wait_for_function(
                        "document.querySelector('.detail-video').readyState>=2 && document.querySelector('.detail-video').currentTime>0"
                    )
                    assert page.locator(".detail-video").evaluate(
                        "e=>[e.duration,e.videoWidth,e.videoHeight]"
                    ) == [5, 1920, 1080]
                page.screenshot(
                    path=str(args.output_dir / "character-layers-detail.png")
                )
                page.keyboard.press("Escape")
                page.goto(
                    url + "#learn/CHARACTER_LAYER_REFINEMENT.md", wait_until="load"
                )
                expect(page.locator(".reader-paper h1")).to_contain_text(
                    "人物受光与材质分层"
                )
                checks.append(
                    "new character-layer review plays both native 1080p60 five-second variants and opens actual implementation notes"
                )

            page.goto(url + "#gallery", wait_until="load")
            page.locator(".hero-feature").click()
            expect(page.locator("#detail-dialog")).to_be_visible()
            page.locator('[data-media="video"]').click()
            video = page.locator(".detail-video")
            page.wait_for_function(
                "document.querySelector('.detail-video').readyState>=2"
            )
            page.wait_for_function(
                "document.querySelector('.detail-video').currentTime>0"
            )
            report["featured_video"] = video.evaluate(
                "e=>({duration:e.duration,width:e.videoWidth,height:e.videoHeight,currentTime:e.currentTime})"
            )
            assert report["featured_video"]["width"] == 1920
            assert abs(report["featured_video"]["duration"] - 5) < 0.1
            page.screenshot(path=str(args.output_dir / "detail-video.png"))
            page.locator(".detail-info .parameter summary").first.click()
            with page.expect_download() as download_info:
                page.locator(".detail-info .parameter>a").first.click()
            config_path = args.output_dir / "recipe-download.json"
            download_info.value.save_as(str(config_path))
            assert (
                json.loads(config_path.read_text(encoding="utf-8"))["id"]
                == "genshin-duet-hall-v3"
            )
            page.evaluate(
                "Object.defineProperty(navigator,'clipboard',{value:undefined,configurable:true})"
            )
            page.locator("[data-copy-project]").click()
            expect(page.locator("#copy-dialog")).to_be_visible()
            assert (
                "Franken_Duet_Reference_Genshin.blend"
                in page.locator("#copy-text").input_value()
            )
            page.keyboard.press("Escape")
            expect(page.locator("#copy-dialog")).not_to_be_visible()
            expect(page.locator("#detail-dialog")).to_be_visible()
            page.keyboard.press("Escape")
            expect(page.locator("#detail-dialog")).not_to_be_visible()
            expect(video).to_have_js_property("paused", True)
            checks.append(
                "real H.264 video plays, JSON download, clipboard fallback, nested Escape and pause on close"
            )

            page.locator('#preset-grid [data-compare="genshin-duet-hall-v3"]').click()
            page.locator('#preset-grid [data-compare="gosari-landscape-v1"]').click()
            page.locator('#preset-grid [data-compare="moonlit-vows-v1"]').click()
            expect(page.locator("#compare-tray-label")).to_have_text("已选 2 / 2 项")
            page.locator("#open-compare").click()
            expect(page.locator("#compare-dialog")).to_be_visible()
            expect(page.locator(".side-by-side figure")).to_have_count(2)
            page.keyboard.press("Escape")
            page.locator("#clear-compare").click()
            page.locator('[data-nav="compare"]').click()
            slider = page.locator(".image-comparison input").first
            slider.focus()
            slider.press("End")
            expect(slider).to_have_value("100")
            assert (
                slider.locator("..").evaluate(
                    "e=>e.style.getPropertyValue('--position')"
                )
                == "100%"
            )
            page.screenshot(path=str(args.output_dir / "comparison.png"))
            checks.append(
                "two-item comparison limit, full-frame side-by-side and keyboard A/B slider"
            )

            page.locator('[data-nav="knowledge"]').click()
            page.locator("#search").fill("SDF")
            assert page.locator(".knowledge-group a").count() > 0
            page.locator("#search").fill("")
            page.goto(url + "#learn/STAGE_ART_NIGHT_STUDY.md", wait_until="load")
            expect(page.locator(".reader-paper h1")).to_have_count(1)
            assert page.locator(".reader-paper table").count() > 0
            assert page.locator(".reader-paper pre code").count() > 0
            assert page.locator(".reader-paper script").count() == 0
            page.locator("#reader-toc-links a").last.click()
            page.goto(url + "#learn/KNOWLEDGE_INDEX.md", wait_until="load")
            page.locator(
                '.reader-paper a[href="#learn/GALLERY_GUIDE.md"]'
            ).first.click()
            expect(page.locator(".reader-paper h1")).to_contain_text("帧间资料库")
            checks.append(
                "knowledge full-text search, safe Markdown tables/code, TOC and internal document routing"
            )

            page.goto(url + "#components", wait_until="load")
            count = page.evaluate("window.MMD_LIBRARY.components.length")
            expect(page.locator(".component-row")).to_have_count(count)
            page.locator("#search").fill("moonlit")
            expect(page.locator(".component-row")).to_have_count(1)
            page.locator("#search").fill("")
            page.goto(url + "#preset/moonlit-vows-v1", wait_until="load")
            expect(page.locator("#detail-dialog")).to_be_visible()
            expect(page.locator(".detail-info h2")).to_have_text("月下 · 冬夜誓言")
            page.locator("[data-copy-command]").click()
            if page.locator("#copy-dialog").is_visible():
                assert (
                    "stage_night_art_lab.py" in page.locator("#copy-text").input_value()
                )
                page.keyboard.press("Escape")
            page.keyboard.press("Escape")
            checks.append(
                "all JSON components, parameter search, deep-link preset and reproducible command"
            )

            if page.evaluate(
                "window.MMD_LIBRARY.entries.some(e=>e.id==='duet-light-space-v1')"
            ):
                page.goto(url + "#preset/duet-light-space-v1", wait_until="load")
                page.locator('[data-media="diagnostic"]').click()
                page.wait_for_function(
                    "document.querySelector('.detail-video').readyState>=2 && document.querySelector('.detail-video').duration===3"
                )
                assert page.locator(".detail-video").evaluate("e=>e.videoWidth") == 960
                page.locator('[data-media="video"]').click()
                page.wait_for_function(
                    "document.querySelector('.detail-video').readyState>=2 && document.querySelector('.detail-video').duration===5"
                )
                assert page.locator(".detail-video").evaluate("e=>e.videoWidth") == 1920
                page.screenshot(
                    path=str(args.output_dir / "quality-revision-detail.png")
                )
                page.keyboard.press("Escape")
                checks.append(
                    "quality revision switches between the real 3s diagnostic and 5s production clip"
                )

            if page.evaluate(
                "window.MMD_LIBRARY.entries.some(e=>e.id==='hesperides-fox-cinema-v1')"
            ):
                page.goto(url + "#preset/hesperides-fox-cinema-v1", wait_until="load")
                expect(page.locator(".detail-info h2")).to_have_text(
                    "夜誓 · 灯光与镜头"
                )
                page.locator('[data-media="video"]').click()
                page.wait_for_function(
                    "document.querySelector('.detail-video').readyState>=2 && document.querySelector('.detail-video').currentTime>0"
                )
                cinema = page.locator(".detail-video").evaluate(
                    "e=>({duration:e.duration,width:e.videoWidth,height:e.videoHeight})"
                )
                assert cinema == {"duration": 5, "width": 1920, "height": 1080}
                page.screenshot(path=str(args.output_dir / "fox-cinema-detail.png"))
                page.keyboard.press("Escape")
                page.goto(url + "#learn/FOX_LIGHTING_AND_CINEMA.md", wait_until="load")
                expect(page.locator(".reader-paper h1")).to_contain_text("亲亲小狐狸")
                assert page.locator(".reader-paper table").count() == 1
                checks.append(
                    "new cinema preset plays native 1080p60 sample and opens its reference study"
                )

            if page.evaluate(
                "window.MMD_LIBRARY.entries.some(e=>e.id==='hesperides-stageart-v2')"
            ):
                page.goto(url + "#preset/hesperides-stageart-v2", wait_until="load")
                expect(page.locator(".detail-info h2")).to_have_text(
                    "入光 · 舞台光影再研究"
                )
                page.locator('[data-media="video"]').click()
                page.wait_for_function(
                    "document.querySelector('.detail-video').readyState>=2 && document.querySelector('.detail-video').currentTime>0"
                )
                assert page.locator(".detail-video").evaluate(
                    "e=>[e.duration,e.videoWidth,e.videoHeight]"
                ) == [5, 1920, 1080]
                page.screenshot(path=str(args.output_dir / "stage-art-detail.png"))
                page.keyboard.press("Escape")
                page.goto(url + "#learn/FOX_STAGE_ART_DEEP_STUDY.md", wait_until="load")
                expect(page.locator(".reader-paper h1")).to_contain_text("小狐狸再研究")
                assert page.locator(".reader-paper table").count() == 1
                checks.append(
                    "stage-art revision plays its final native sample and opens the deeper study"
                )

            if page.evaluate(
                "window.MMD_LIBRARY.entries.some(e=>e.id==='duet-captions-focused-v1')"
            ):
                page.goto(url + "#preset/duet-captions-focused-v1", wait_until="load")
                expect(page.locator(".detail-info h2")).to_have_text(
                    "字入光 · 官方动效与冷暖舞台"
                )
                page.locator('[data-media="video"]').click()
                page.wait_for_function(
                    "document.querySelector('.detail-video').readyState>=2 && document.querySelector('.detail-video').currentTime>0"
                )
                assert page.locator(".detail-video").evaluate(
                    "e=>[e.duration,e.videoWidth,e.videoHeight]"
                ) == [5, 1920, 1080]
                page.screenshot(path=str(args.output_dir / "captions-detail.png"))
                expect(page.locator('[data-media="diagnostic"]')).to_have_text(
                    "无字幕灯光版 · 5s"
                )
                page.locator('[data-media="diagnostic"]').click()
                page.wait_for_function(
                    "document.querySelector('.detail-video').readyState>=2 && document.querySelector('.detail-video').currentTime>0 && document.querySelector('.detail-video').src.includes('-diagnostic.mp4')"
                )
                assert page.locator(".detail-video").evaluate(
                    "e=>[e.duration,e.videoWidth,e.videoHeight]"
                ) == [5, 1920, 1080]
                page.keyboard.press("Escape")
                page.goto(
                    url + "#learn/DUET_CAPTION_STABILITY_AND_LIGHTING.md",
                    wait_until="load",
                )
                expect(page.locator(".reader-paper h1")).to_contain_text("官方动效字幕")
                assert page.locator(".reader-paper table").count() == 2
                checks.append(
                    "official-caption preset plays both real five-second variants with correct labels and opens the study"
                )

            if page.evaluate(
                "window.MMD_LIBRARY.entries.some(e=>e.id==='duet-soft-top-rim-v1')"
            ):
                page.goto(url + "#preset/duet-soft-top-rim-v1", wait_until="load")
                expect(page.locator(".detail-info h2")).to_have_text(
                    "柔映 · 顶光与逆光"
                )
                for kind in ("video", "diagnostic"):
                    page.locator(f'[data-media="{kind}"]').click()
                    page.wait_for_function(
                        "document.querySelector('.detail-video').readyState>=2 && document.querySelector('.detail-video').currentTime>0"
                    )
                    assert page.locator(".detail-video").evaluate(
                        "e=>[e.duration,e.videoWidth,e.videoHeight]"
                    ) == [5, 1920, 1080]
                page.screenshot(path=str(args.output_dir / "soft-top-rim-detail.png"))
                page.keyboard.press("Escape")
                page.goto(url + "#learn/SOFT_TOP_RIM_LIGHTING.md", wait_until="load")
                expect(page.locator(".reader-paper h1")).to_contain_text(
                    "柔光、顶光与逆光"
                )
                assert page.locator(".reader-paper table").count() == 1
                checks.append(
                    "soft-top/rim revision plays both native five-second variants and opens its lighting recipe"
                )

            if page.evaluate(
                "window.MMD_LIBRARY.entries.some(e=>e.id==='duet-blue-gold-wedding-v1')"
            ):
                page.goto(url + "#preset/duet-blue-gold-wedding-v1", wait_until="load")
                expect(page.locator(".detail-info h2")).to_have_text("誓光 · 蓝金婚礼")
                for kind in ("video", "diagnostic"):
                    page.locator(f'[data-media="{kind}"]').click()
                    page.wait_for_function(
                        "document.querySelector('.detail-video').readyState>=2 && document.querySelector('.detail-video').currentTime>0"
                    )
                    assert page.locator(".detail-video").evaluate(
                        "e=>[e.duration,e.videoWidth,e.videoHeight]"
                    ) == [5, 1920, 1080]
                page.screenshot(
                    path=str(args.output_dir / "blue-gold-wedding-detail.png")
                )
                page.keyboard.press("Escape")
                page.goto(url + "#learn/BLUE_GOLD_WEDDING_STUDY.md", wait_until="load")
                expect(page.locator(".reader-paper h1")).to_contain_text("蓝金婚礼")
                assert page.locator(".reader-paper table").count() == 1
                checks.append(
                    "blue-gold wedding revision plays both native variants and opens its three-point, volume and caption study"
                )

            if page.evaluate(
                "window.MMD_LIBRARY.entries.some(e=>e.id==='duet-grounded-color-v1')"
            ):
                page.goto(url + "#preset/duet-grounded-color-v1", wait_until="load")
                expect(page.locator(".detail-info h2")).to_have_text(
                    "落影 · 接地与色彩"
                )
                for kind in ("video", "diagnostic"):
                    page.locator(f'[data-media="{kind}"]').click()
                    page.wait_for_function(
                        "document.querySelector('.detail-video').readyState>=2 && document.querySelector('.detail-video').currentTime>0"
                    )
                    assert page.locator(".detail-video").evaluate(
                        "e=>[e.duration,e.videoWidth,e.videoHeight]"
                    ) == [5, 1920, 1080]
                page.screenshot(path=str(args.output_dir / "grounded-color-detail.png"))
                page.keyboard.press("Escape")
                page.goto(
                    url + "#learn/SHADOW_GROUNDING_AND_PLAYBACK_COLOR.md",
                    wait_until="load",
                )
                expect(page.locator(".reader-paper h1")).to_contain_text("人物自阴影")
                checks.append(
                    "grounded/color revision plays both explicit-SDR videos and opens its shadow/color study"
                )

            page.goto(url + "#gallery", wait_until="load")
            page.locator("#theme-toggle").click()
            assert page.locator("html").get_attribute("data-theme") == "light"
            page.reload(wait_until="load")
            assert page.locator("html").get_attribute("data-theme") == "light"
            page.screenshot(path=str(args.output_dir / "desktop-light.png"))
            page.locator("#theme-toggle").click()
            page.locator("#main").focus()
            page.keyboard.press("/")
            expect(page.locator("#search")).to_be_focused()
            page.set_viewport_size({"width": 390, "height": 844})
            page.locator("#search").blur()
            page.screenshot(path=str(args.output_dir / "mobile.png"))
            assert page.evaluate("document.documentElement.scrollWidth<=innerWidth"), (
                "Mobile gallery overflow"
            )
            page.goto(url + "#learn/STAGE_ART_NIGHT_STUDY.md", wait_until="load")
            assert page.evaluate("document.documentElement.scrollWidth<=innerWidth"), (
                "Mobile reader overflow"
            )
            checks.append(
                "persisted light/dark theme, slash shortcut, 390px mobile gallery and document fit"
            )
            assert not requests, requests
            assert not errors, errors
            report["passed"] = True
            report["browser"] = browser.version
            report["entries"] = total
            report["components"] = count
            browser.close()
    finally:
        (args.output_dir / "browser-report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
