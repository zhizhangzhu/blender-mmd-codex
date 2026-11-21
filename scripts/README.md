# 脚本导航

自动生成；从[当前状态](../catalog/current_state.json)确认工程，再读[工具输入契约](../docs/TOOL_AND_PRESET_MAP.md)。版本脚本保留原路径，避免破坏导入。以下分类和副作用提示是静态启发式，不能替代源码审查。

## 日常入口

```powershell
python -m scripts.repository_index --check
python -m scripts.audit_knowledge
python -m scripts.mmd_studio status
python -m scripts.mmd_studio context --task reference --query "白衣 发束"
python -m scripts.mmd_studio lessons --task lighting --query "舞台 白衣"
python -m scripts.learning_queue plan --limit 3
```

索引工具不执行被扫描的脚本。`--write`只更新索引；`audit_knowledge --output`写报告。诊断脚本仍可能渲染或启动子进程。当前原生MME实验为[方案](../docs/MME_NATIVE_LEARNING_LAB.md)，没有可用的一键MMD主渲承诺。

## 制作、图审与经验闭环（5）

| 文件 | 模块说明 | 静态提示 |
| --- | --- | --- |
| [studio_iteration.py](studio_iteration.py) | Explicit, bounded reference experiments; no visual judgments are inferred. | 未检出上述关键字；仍需读源码 |
| [studio_lessons.py](studio_lessons.py) | Explicit registration and integrity-checked retrieval of single-case lessons. | 未检出上述关键字；仍需读源码 |
| [studio_publish.py](studio_publish.py) | Explicit isolated candidate publication and independent reopen launcher (stdlib). | starts_external_process, writes_text_files |
| [studio_publish_worker.py](studio_publish_worker.py) | Pinned Blender worker for a new, bounded still candidate and its reopen. | native_render_call, saves_blend |
| [studio_review_board.py](studio_review_board.py) | Offline, pinned iteration review boards; never records visual approval. | 未检出上述关键字；仍需读源码 |

## 查询与维护入口（9）

| 文件 | 模块说明 | 静态提示 |
| --- | --- | --- |
| [audit_knowledge.py](audit_knowledge.py) | Validate current production facts, knowledge links and offline packaging. | references_current_state |
| [knowledge_route.py](knowledge_route.py) | Read task knowledge routes without importing production code or starting tools. | 未检出上述关键字；仍需读源码 |
| [learning_queue.py](learning_queue.py) | Check and resume the MMD learning queue offline; never run experiments or fetch URLs. | 未检出上述关键字；仍需读源码 |
| [mmd_studio.py](mmd_studio.py) | Read-only entry to studio knowledge, current scope, reference studies and learning. | references_current_state |
| [reference_study.py](reference_study.py) | Prepare local reference evidence, separate observations from hypotheses, and build a design brief. | starts_external_process, writes_text_files |
| [repository_index.py](repository_index.py) | Index repository files without importing or executing production scripts. | writes_text_files, references_current_state |
| [studio_registry.py](studio_registry.py) | Read-only studio evidence registry. Structural checks are not art approval. | references_current_state |
| [studio_scene_contract.py](studio_scene_contract.py) | Read-only bounded scene benchmark contract (stdlib only). | 未检出上述关键字；仍需读源码 |
| [studio_tasks.py](studio_tasks.py) | Planning-only model recommendations and bounded task packets (stdlib only). | 未检出上述关键字；仍需读源码 |

## 版本登记与打包（39）

| 文件 | 模块说明 | 静态提示 |
| --- | --- | --- |
| [complete_goo_eye_hair_stage_preview.py](complete_goo_eye_hair_stage_preview.py) | Wait for the existing orphaned render, then encode its completed native cache. | 未检出上述关键字；仍需读源码 |
| [complete_goo_tyndall_production.py](complete_goo_tyndall_production.py) | Explicit volume light groups for the actual Goo direct-light packing path. | native_render_call, saves_blend, writes_text_files |
| [finish_goo_window_shafts.py](finish_goo_window_shafts.py) | Remove broad air illumination and use a bounded constant-density control for shafts. | native_render_call, saves_blend, writes_text_files |
| [finish_grounded_review.py](finish_grounded_review.py) | Composite, encode and verify a bounded 300-frame duet SDR review. | starts_external_process |
| [package_blue_gold_wedding.py](package_blue_gold_wedding.py) | Package verified wedding lighting and blue/gold official typography. | writes_text_files |
| [package_character_layers_review.py](package_character_layers_review.py) | Register an actually rendered and reviewed character-layer study in Atlas. | writes_text_files, references_current_state |
| [package_clean_game_duet.py](package_clean_game_duet.py) | Validate and register only the completed clean-character, no-arc five seconds. | references_current_state |
| [package_duet_captions.py](package_duet_captions.py) | Package the verified official-caption study and add its offline Atlas entry. | writes_text_files |
| [package_duet_delivery.py](package_duet_delivery.py) | Publish local delivery notes only after the full movie passes verification. | writes_text_files |
| [package_face_ink.py](package_face_ink.py) | Archive a verified eight-second face-ink refinement and its exact recipe. | writes_text_files |
| [package_fox_cinema.py](package_fox_cinema.py) | Publish only the verified five-second cinema study and its real comparisons. | writes_text_files |
| [package_fox_stageart.py](package_fox_stageart.py) | Archive and catalog the verified second fox lighting study. | writes_text_files |
| [package_goo_daylight_v2.py](package_goo_daylight_v2.py) | Package the v2 study and preservation evidence; finalize only after encoding. | writes_text_files, references_current_state |
| [package_goo_eye_hair_stage.py](package_goo_eye_hair_stage.py) | Finalize only an actually encoded eye/hair/stage sample; no MP4 decoding. | writes_text_files, references_current_state |
| [package_goo_feature_study.py](package_goo_feature_study.py) | Collect existing isolated research evidence; does not load Blender or production media. | writes_text_files, references_current_state |
| [package_goo_rim_glow.py](package_goo_rim_glow.py) | Finalize the actual encoded rim/glow review sample without post-output video QA. | writes_text_files, references_current_state |
| [package_goo_tyndall_rim.py](package_goo_tyndall_rim.py) | Register the finished actual encoded sample; never decode or watch output media. | writes_text_files, references_current_state |
| [package_goo_window_wrap.py](package_goo_window_wrap.py) | Record the user's revision request, or finalize the actual encoded window-wrap sample. | writes_text_files, references_current_state |
| [package_goo_working_project.py](package_goo_working_project.py) | Write local user launchers and migration facts; never claim video completion before encoding. | writes_text_files, references_current_state |
| [package_grounded_review.py](package_grounded_review.py) | Package the verified shadow/color review without replacing accepted baselines. | writes_text_files |
| [package_ikhor_sleeve_review.py](package_ikhor_sleeve_review.py) | Encode the diagnostic wrists and make explicitly sampled contact sheets. | starts_external_process, writes_text_files |
| [package_ikhor_wedding.py](package_ikhor_wedding.py) | Register only the completed, hash-bound Aksiniya/Ikhor five-second review. | writes_text_files, references_current_state |
| [package_portrait_relight.py](package_portrait_relight.py) | Register the completed portrait still, never replacing the latest video. | writes_text_files, references_current_state |
| [package_quality_upgrade.py](package_quality_upgrade.py) | Publish a verified local quality revision into the reusable offline catalog. | writes_text_files |
| [package_reference_transfer.py](package_reference_transfer.py) | Register the completed bounded reference-transfer review, preserving history. | writes_text_files, references_current_state |
| [package_soft_top_rim.py](package_soft_top_rim.py) | Archive a verified soft-top/rim revision with actual lighting comparisons. | writes_text_files |
| [package_stage_wuwa_study.py](package_stage_wuwa_study.py) | Package original notes and rendered comparisons; preserve the accepted movie. | writes_text_files |
| [package_style_suite.py](package_style_suite.py) | Archive a completed six-package style study after actual media verification. | writes_text_files |
| [package_surface_refinement.py](package_surface_refinement.py) | Archive completed surface refinement media and the exact reviewed controls. | writes_text_files |
| [record_citlali_fringe_stills.py](record_citlali_fringe_stills.py) | Record completed warm-fringe stills and the user's standing still-only policy. | writes_text_files, references_current_state |
| [record_goo_blender_foundations.py](record_goo_blender_foundations.py) | Record the bounded input/display experiments and official reading, not production gains. | writes_text_files, references_current_state |
| [record_goo_foundation_study.py](record_goo_foundation_study.py) | Record actual Goo foundation reading and isolated controls, not full mastery. | writes_text_files, references_current_state |
| [record_goo_reference_normal_study.py](record_goo_reference_normal_study.py) | Record reference observations and the bounded Normal-input experiment. | writes_text_files, references_current_state |
| [record_goo_toon_candidate.py](record_goo_toon_candidate.py) | Record the verified opaque-toon candidate without claiming a new video exists. | writes_text_files, references_current_state |
| [record_ikhor_brightness_v6.py](record_ikhor_brightness_v6.py) | Record the second user-requested Ikhor brightness reduction, stills only. | writes_text_files, references_current_state |
| [record_ikhor_hair_still.py](record_ikhor_hair_still.py) | Publish only completed stills; retain the old video as rejected hair alignment history. | writes_text_files, references_current_state |
| [record_mme_balanced_stills.py](record_mme_balanced_stills.py) | Record the observed overbright feedback and bounded still correction. | writes_text_files, references_current_state |
| [record_mme_reference_light_stills.py](record_mme_reference_light_stills.py) | Publish the observed native-Goo MME-inspired still candidate; never encode video. | writes_text_files, references_current_state |
| [record_repository_organization.py](record_repository_organization.py) | Record organization and route research; never execute or modify a scene. | writes_text_files, references_current_state |

## 版本制作与迁移（46）

| 文件 | 模块说明 | 静态提示 |
| --- | --- | --- |
| [add_goo_window_gobo.py](add_goo_window_gobo.py) | Add an off-camera physical window-pattern lighting accessory to Goo v2. | native_render_call, saves_blend, writes_text_files |
| [apply_fox_cinema.py](apply_fox_cinema.py) | Build an independent lighting, focus and shutter study from the repaired master. | native_render_call, saves_blend, writes_text_files |
| [apply_fox_stageart.py](apply_fox_stageart.py) | Develop the reviewed fox study into a shadowed, spatially coherent stage. | native_render_call, saves_blend, writes_text_files |
| [apply_ikhor_sleeve_repair.py](apply_ikhor_sleeve_repair.py) | Apply only a separately tested sleeve Action to the rejected v4 master. | saves_blend, writes_text_files |
| [finalize_citlali_fringe_still.py](finalize_citlali_fringe_still.py) | Combine the observed actor-specific fringe settings and render only stills. | native_render_call, saves_blend, writes_text_files |
| [finalize_face_contract.py](finalize_face_contract.py) | Fix the adapted Face Factor's incoming-vector contract in a new master. | native_render_call, saves_blend, writes_text_files |
| [finalize_goo_character_lookdev.py](finalize_goo_character_lookdev.py) | Finalize the pinned v3 character still and independently reopen it. | saves_blend, writes_text_files |
| [finalize_goo_preview.py](finalize_goo_preview.py) | Record a successfully encoded preview, without decoding or inspecting the output video. | writes_text_files, references_current_state |
| [finalize_goo_toon_shadow_master.py](finalize_goo_toon_shadow_master.py) | Relocate the baked shadow sequences without Blender remapping them to the source folder. | saves_blend, writes_text_files |
| [finalize_goo_tyndall_look.py](finalize_goo_tyndall_look.py) | Fix volume collection visibility and compress highlights with a fixed Reinhard shoulder. | native_render_call, saves_blend, writes_text_files |
| [finalize_mme_light_hero_stills.py](finalize_mme_light_hero_stills.py) | Protect original trim masks and compare restrained versus stronger diffusion. | native_render_call, saves_blend, writes_text_files |
| [integrate_ikhor_wedding.py](integrate_ikhor_wedding.py) | Replace the Hina slot with an independently baked Ikhor in a new hall copy. | native_render_call, saves_blend, writes_text_files |
| [integrate_light_space.py](integrate_light_space.py) | Repair fixture transforms and head axes, then connect bounded real shading. | native_render_call, saves_blend, writes_text_files |
| [integrate_reference_duet.py](integrate_reference_duet.py) | Integrate the tested hall and bounded character study; preserve animation. | native_render_call, saves_blend, writes_text_files |
| [prepare_aether_production.py](prepare_aether_production.py) | Save the revised Aether scene as a fresh, explicitly recorded production file. | saves_blend, writes_text_files |
| [prepare_blue_gold_wedding.py](prepare_blue_gold_wedding.py) | Add wedding shafts, luminous aisle accents and isolated highlight halos. | native_render_call, saves_blend, writes_text_files |
| [prepare_bold_wedding.py](prepare_bold_wedding.py) | Create a fingerprint-bound, independently saved bold wedding-lighting revision. | native_render_call, saves_blend, writes_text_files |
| [prepare_character_layers.py](prepare_character_layers.py) | Unify one actor color/lighting/AO/highlight contract in an independent copy. | native_render_call, saves_blend, writes_text_files |
| [prepare_clean_game_duet.py](prepare_clean_game_duet.py) | Build a new, character-only clean NPR revision from the caption-fixed v7. | saves_blend, writes_text_files |
| [prepare_duet_caption_lighting.py](prepare_duet_caption_lighting.py) | Build responsive stage lighting and native matte/beauty caches for captions. | native_render_call, saves_blend, writes_text_files |
| [prepare_goo_daylight_v2.py](prepare_goo_daylight_v2.py) | Revise only the pinned Goo v1 copy after the MME lighting study. | native_render_call, saves_blend, writes_text_files |
| [prepare_goo_eye_hair_stage.py](prepare_goo_eye_hair_stage.py) | Build bounded eye animation, eye shading/peek, hair shadows and stage surfaces. | native_render_call, saves_blend, writes_text_files |
| [prepare_goo_opaque_toon_v11.py](prepare_goo_opaque_toon_v11.py) | Restore original opaque hair and add compact toon ramps with face shadow masks. | native_render_call, saves_blend, writes_text_files |
| [prepare_goo_toon_face_hair_study.py](prepare_goo_toon_face_hair_study.py) | Opaque hair, toon value ramps and geometry-derived face hair-shadow study. | saves_blend, writes_text_files |
| [prepare_goo_tyndall_rim.py](prepare_goo_tyndall_rim.py) | Continue the requested rim/glow revision with bounded shadowed window air. | native_render_call, saves_blend, writes_text_files |
| [prepare_goo_window_wrap.py](prepare_goo_window_wrap.py) | Replace the rejected narrow shafts with surveyed-window daylight and a stronger NPR rim. | native_render_call, saves_blend, writes_text_files |
| [prepare_graphic_self_shadows.py](prepare_graphic_self_shadows.py) | Refine native hull ink and connect readable geometric self-shadow to NPR. | native_render_call, saves_blend, writes_text_files |
| [prepare_grounded_shadows.py](prepare_grounded_shadows.py) | Restore visible cast/contact shadows and bounded actor self-shadow response. | native_render_call, saves_blend, writes_text_files |
| [prepare_ikhor_motion.py](prepare_ikhor_motion.py) | Import Ikhor's native Hina VMD and prepare a separately audited motion candidate. | saves_blend |
| [prepare_mme_reference_light_stills.py](prepare_mme_reference_light_stills.py) | MME-inspired light/palette/diffusion adaptation; native Goo stills only. | native_render_call, saves_blend, writes_text_files |
| [prepare_portrait_relight.py](prepare_portrait_relight.py) | Build a new hash-bound portrait relight and render bounded stills only. | native_render_call, saves_blend, writes_text_files |
| [prepare_quality_render.py](prepare_quality_render.py) | Reopen the integrated master, validate scene persistence and archive naming. | native_render_call, saves_blend, writes_text_files |
| [prepare_reference_transfer.py](prepare_reference_transfer.py) | Port bounded NPR/light/material principles into a new Character Layers copy. | native_render_call, saves_blend, writes_text_files |
| [prepare_soft_top_rim.py](prepare_soft_top_rim.py) | Add broad soft fill, overhead illumination and a controlled rear rim. | native_render_call, saves_blend, writes_text_files |
| [prepare_surface_motion.py](prepare_surface_motion.py) | Extend the reviewed surface scene to an eight-second portrait camera study. | saves_blend, writes_text_files |
| [refine_goo_character_lookdev.py](refine_goo_character_lookdev.py) | Fixed-v6, reversible character look development. Static 4290 only; no video. | native_render_call, saves_blend, writes_text_files |
| [refine_goo_opaque_toon.py](refine_goo_opaque_toon.py) | Repair legacy ramp insertion and refine the face-shadow footprint. | saves_blend, writes_text_files |
| [refine_goo_tyndall_visibility.py](refine_goo_tyndall_visibility.py) | Make the requested window shafts readable with explicit art-directed light linking. | native_render_call, saves_blend, writes_text_files |
| [refine_ikhor_skin.py](refine_ikhor_skin.py) | Compare a bounded skin-shadow calibration and save only a new review copy. | native_render_call, saves_blend, writes_text_files |
| [refine_mme_reference_light_stills.py](refine_mme_reference_light_stills.py) | Remove failed global grading; retain restrained light and material changes. | native_render_call, saves_blend, writes_text_files |
| [refine_reference_duet.py](refine_reference_duet.py) | Refine the NPC SDF mapping and shadow cost before the 5-second render. | native_render_call, saves_blend, writes_text_files |
| [repair_duet_caption_targets.py](repair_duet_caption_targets.py) | Repair stale character names in the caption-only Cryptomatte selection. | saves_blend, writes_text_files |
| [repair_ikhor_hair_alignment.py](repair_ikhor_hair_alignment.py) | Isolate baked hair translation errors; render still-only controls. | native_render_call, writes_text_files |
| [repair_quality_archive_frame.py](repair_quality_archive_frame.py) | Rerender an explicitly requested master frame and its native linear archive. | native_render_call |
| [restrain_ikhor_mme_still.py](restrain_ikhor_mme_still.py) | Reduce Ikhor's added palette gain without changing Aksiniya or global exposure. | native_render_call, saves_blend, writes_text_files |
| [save_ikhor_aligned_hair_still.py](save_ikhor_aligned_hair_still.py) | Restore original hair bind pose in a still-only, independently saved project. | native_render_call, saves_blend, writes_text_files |

## 渲染与视频输出（25）

| 文件 | 模块说明 | 静态提示 |
| --- | --- | --- |
| [assemble_render_chunks.py](assemble_render_chunks.py) | Join independently rendered, contiguous video chunks without recompression. | starts_external_process |
| [encode_review_cache.py](encode_review_cache.py) | Encode native display-sRGB beauty caches with an explicit SDR color contract. | starts_external_process |
| [mux_production_audio.py](mux_production_audio.py) | Mix a selected BGM segment into an existing video without rerendering. | starts_external_process |
| [render_blender53_author_face_controls.py](render_blender53_author_face_controls.py) | Pinned author-Furina diagnostic stills, primary face SDF on/off; never save blend. | native_render_call, writes_text_files |
| [render_camera_preview.py](render_camera_preview.py) | Render the open draft's frame range as a small, silent H.264 camera preview. | native_render_call |
| [render_character_layer_controls.py](render_character_layer_controls.py) | Render bounded same-frame layer ablations without saving the production file. | native_render_call, writes_text_files |
| [render_clean_game_controls.py](render_clean_game_controls.py) | Unblurred, same-pose material controls; never save the production scene. | native_render_call, writes_text_files |
| [render_duet_chunk.py](render_duet_chunk.py) | Render one recoverable production chunk and expose progress as JSON. | native_render_call, writes_text_files |
| [render_duet_full.py](render_duet_full.py) | Render full-song chunks, validate/join them, mux selected FLAC, then verify. | starts_external_process, writes_text_files |
| [render_duet_sample.py](render_duet_sample.py) | Render a bounded duet review clip, reuse verified matching chunks, and verify. | starts_external_process, writes_text_files |
| [render_ikhor_duet_matte.py](render_ikhor_duet_matte.py) | Render native duet Cryptomatte and Alpha from pinned v6/v7, without saving. | native_render_call, writes_text_files |
| [render_ikhor_sleeve_review.py](render_ikhor_sleeve_review.py) | Render both wrists continuously from a saved, portable repair candidate. | native_render_call, writes_text_files |
| [render_portrait_light_controls.py](render_portrait_light_controls.py) | Render three fingerprint-bound portrait controls without saving a blend. | native_render_call, writes_text_files |
| [render_portrait_quick_cache.py](render_portrait_quick_cache.py) | Render the saved portrait look directly to new caption caches; no QA pass. | native_render_call, writes_text_files |
| [render_production.py](render_production.py) | Render a saved production project to a new H.264 picture master. | native_render_call |
| [render_reference_transfer_controls.py](render_reference_transfer_controls.py) | Render same-frame ablations of the new reference transfer without saving. | native_render_call, writes_text_files |
| [render_saved_portrait.py](render_saved_portrait.py) | Render the saved portrait candidate in a fresh process without rebuilding it. | native_render_call, writes_text_files |
| [render_shader_diagnostics.py](render_shader_diagnostics.py) | Render three controlled motion probes on an unsaved independent scene copy. | native_render_call, starts_external_process, writes_text_files |
| [render_sunlit_floor_study.py](render_sunlit_floor_study.py) | Temporary full-body framing to make the requested floor shadows visible. | native_render_call |
| [run_goo_daylight_v2_preview.py](run_goo_daylight_v2_preview.py) | One-shot Goo daylight v2 captioned sample entry. | 未检出上述关键字；仍需读源码 |
| [run_goo_eye_hair_stage_preview.py](run_goo_eye_hair_stage_preview.py) | Render the saved eye/hair/stage revision as one captioned original-vocal sample. | 未检出上述关键字；仍需读源码 |
| [run_goo_rim_glow_preview.py](run_goo_rim_glow_preview.py) | Render the saved rim/highlight/glow revision as one captioned five-second sample. | 未检出上述关键字；仍需读源码 |
| [run_goo_tyndall_rim_preview.py](run_goo_tyndall_rim_preview.py) | Render the final window-air / white-blue rim look from its saved Goo master. | 未检出上述关键字；仍需读源码 |
| [run_goo_wedding_preview.py](run_goo_wedding_preview.py) | Explicit one-shot entry: Goo 1080p30, five seconds, captions and original vocal audio. | 未检出上述关键字；仍需读源码 |
| [run_goo_window_wrap_preview.py](run_goo_window_wrap_preview.py) | Render the broad-window, stronger-rim revision from the saved Goo master. | 未检出上述关键字；仍需读源码 |

## 探针与诊断（74）

| 文件 | 模块说明 | 静态提示 |
| --- | --- | --- |
| [abnormal_probe.py](abnormal_probe.py) | Temporarily register a pinned Abnormal source in an isolated process. | 未检出上述关键字；仍需读源码 |
| [audit_chest_binding.py](audit_chest_binding.py) | Read full model/rigid bindings to identify supported chest motion chains. | writes_text_files |
| [audit_duet_caption_coverage.py](audit_duet_caption_coverage.py) | Read-only semantic head/body ROI audit for a duet caption actor cache. | writes_text_files |
| [audit_ikhor_sleeve_geometry.py](audit_ikhor_sleeve_geometry.py) | Read-only geometric audit of Ikhor's wrist/cuff relationship. | writes_text_files |
| [audit_review_color.py](audit_review_color.py) | Compare actual compositor RGB with explicitly decoded video color matrices. | starts_external_process, writes_text_files |
| [audit_stage_archive.py](audit_stage_archive.py) | Test/extract a downloaded stage archive and compare it with existing assets. | starts_external_process, writes_text_files |
| [brightness_scene_probe.py](brightness_scene_probe.py) | Inspect reachable emission, lighting and color transforms on the same HDR frame. | native_render_call, writes_text_files |
| [check_goo_rendered_shadow_aovs.py](check_goo_rendered_shadow_aovs.py) | Verify actual shader texture sequence sampling using raw face UV/value AOVs. | writes_text_files |
| [cinema_scene_probe.py](cinema_scene_probe.py) | Read camera, lighting and motion controls without modifying the source file. | writes_text_files |
| [diagnose_actor_light.py](diagnose_actor_light.py) | Measure the actual unclipped native actor illumination and material classes. | native_render_call |
| [diagnose_goo_hair_shadow_toplight.py](diagnose_goo_hair_shadow_toplight.py) | Read current shadow routing and render isolated glare/highlight/toplight controls. | native_render_call |
| [diagnose_goo_production_beams.py](diagnose_goo_production_beams.py) | Separate geometry visibility and final compositing from direct volume rendering. | native_render_call, writes_text_files |
| [diagnose_goo_volume_shader.py](diagnose_goo_volume_shader.py) | Factory-only positive control for Goo direct volume light support. | native_render_call, writes_text_files |
| [diagnose_opaque_hair.py](diagnose_opaque_hair.py) | Compare opaque closures and isolate a silver-hair regression in fresh renders. | native_render_call |
| [diagnose_projected_eye_alpha.py](diagnose_projected_eye_alpha.py) | Measure actual eye-peek, native head shadows and raw/final alpha response. | native_render_call, writes_text_files |
| [duet_region_probe.py](duet_region_probe.py) | Compare native full and cropped renders before considering local revisions. | native_render_call, writes_text_files |
| [genshin_character_probe.py](genshin_character_probe.py) | Inventory actual duet material inputs before adapting game-style shading. | writes_text_files |
| [genshin_library_probe.py](genshin_library_probe.py) | Read festivities' downloaded node library without executing embedded code. | writes_text_files |
| [hesperides_reference_probe.py](hesperides_reference_probe.py) | Read camera-ray intersections and render the world alone for sky diagnosis. | native_render_call, writes_text_files |
| [inspect_blender53_toon_package.py](inspect_blender53_toon_package.py) | Read a pinned private toon package with scripts disabled; never render/save it. | writes_text_files |
| [inspect_character_lookdev.py](inspect_character_lookdev.py) | Read the fixed current Goo still before making isolated look-development copies. | writes_text_files |
| [inspect_ikhor_hair_alignment.py](inspect_ikhor_hair_alignment.py) | No module description; read source before use | 未检出上述关键字；仍需读源码 |
| [mmd_caption_probe.py](mmd_caption_probe.py) | Inspect locally supported compositor matte and text-output APIs. | 未检出上述关键字；仍需读源码 |
| [mmd_duet_layout_probe.py](mmd_duet_layout_probe.py) | Import the assigned full duet and an authored camera for draft layout QA. | native_render_call, saves_blend, writes_text_files |
| [mmd_quality_probe.py](mmd_quality_probe.py) | Read local NPR/AO/normal/plugin compatibility before changing a scene. | 未检出上述关键字；仍需读源码 |
| [mmd_surface_probe.py](mmd_surface_probe.py) | Inspect actual source maps, material regions and head space for refinement. | writes_text_files |
| [mmd_tutorial_probe.py](mmd_tutorial_probe.py) | Read local Blender APIs needed by the tutorial lighting/outline lab. | 未检出上述关键字；仍需读源码 |
| [probe_actor_ink_shadow.py](probe_actor_ink_shadow.py) | Inspect the current actor hull and the preset's actual shadow sockets. | writes_text_files |
| [probe_bold_wedding.py](probe_bold_wedding.py) | Read-only inventory for the bounded bold-wedding lighting revision. | 未检出上述关键字；仍需读源码 |
| [probe_character_layer_contract.py](probe_character_layer_contract.py) | Read live character shader paths without rendering or saving the source. | writes_text_files |
| [probe_current_stage_surfaces.py](probe_current_stage_surfaces.py) | Identify real stage surfaces by rays through the delivered camera. | writes_text_files |
| [probe_face_direction.py](probe_face_direction.py) | Compare Face Factor light-direction conventions in independent stills. | native_render_call, writes_text_files |
| [probe_fox_stage.py](probe_fox_stage.py) | Audit real ground surfaces, existing light linking and compositor routing. | writes_text_files |
| [probe_goo_addon_functions.py](probe_goo_addon_functions.py) | Exercise selected add-on operations in a disposable Goo scene, without rendering. | writes_text_files |
| [probe_goo_daylight.py](probe_goo_daylight.py) | Read-only light, material and sky inventory for the next Goo study. | writes_text_files |
| [probe_goo_migration.py](probe_goo_migration.py) | Read-only Goo runtime/add-on and project compatibility probe; no preferences saved. | writes_text_files |
| [probe_goo_shadow_budget.py](probe_goo_shadow_budget.py) | Read the current build's actual shadow budget controls. | 未检出上述关键字；仍需读源码 |
| [probe_goo_sun_direction.py](probe_goo_sun_direction.py) | Find architectural openings from the performance floor by geometric rays. | writes_text_files |
| [probe_goo_volume_visibility.py](probe_goo_volume_visibility.py) | Read actual volume toggles and view-layer visibility without rendering or saving. | writes_text_files |
| [probe_goo_window_wrap.py](probe_goo_window_wrap.py) | Read real window mesh islands and existing hair/rim controls, without rendering. | writes_text_files |
| [probe_ikhor_caption_matte.py](probe_ikhor_caption_matte.py) | Read-only inventory of the active caption matte graph and PNG coverage. | writes_text_files |
| [probe_ikhor_hair_morphs.py](probe_ikhor_hair_morphs.py) | No module description; read source before use | 未检出上述关键字；仍需读源码 |
| [probe_jelly_eye_compatibility.py](probe_jelly_eye_compatibility.py) | Exercise the user's privately cached add-on without installing preferences. | saves_blend, writes_text_files |
| [probe_mme_reference_relight.py](probe_mme_reference_relight.py) | No module description; read source before use | 未检出上述关键字；仍需读源码 |
| [probe_shadow_grounding.py](probe_shadow_grounding.py) | Read actual light, material, foot and floor data before grounding changes. | writes_text_files |
| [probe_stage_focal_targets.py](probe_stage_focal_targets.py) | Locate actual rendered surfaces under image-space lighting targets. | writes_text_files |
| [probe_toon_hair_routes.py](probe_toon_hair_routes.py) | No module description; read source before use | 未检出上述关键字；仍需读源码 |
| [quality_pipeline_probe.py](quality_pipeline_probe.py) | Audit current light/shader/layer capabilities without saving the source blend. | writes_text_files |
| [snapshot_goo_scene.py](snapshot_goo_scene.py) | Compact migration evidence: complete curve data/geometry and sampled evaluated poses. | writes_text_files |
| [studio_bench.py](studio_bench.py) | Opt-in, bounded Blender scene benchmark launcher (stdlib only). | starts_external_process, writes_text_files |
| [studio_scene_worker.py](studio_scene_worker.py) | Blender-only isolated scene inspection and explicitly mapped static controls. | native_render_call, writes_text_files |
| [verify_audio_blender.py](verify_audio_blender.py) | Decode the finished MP4 audio using Blender's Audaspace/FFmpeg runtime. | 未检出上述关键字；仍需读源码 |
| [verify_caption_master.py](verify_caption_master.py) | Reopen the focused-light master and verify motion and cache isolation. | 未检出上述关键字；仍需读源码 |
| [verify_character_diagnostics.py](verify_character_diagnostics.py) | Decode bounded three-axis tests and export face strips for honest visual QA. | writes_text_files |
| [verify_character_layer_master.py](verify_character_layer_master.py) | Read-only native audit of a source and rebuilt character-layer master. | writes_text_files |
| [verify_clean_caption_coverage.py](verify_clean_caption_coverage.py) | Check current actor PNGs at SHA-bound, inherited identical-camera/pose ROIs. | writes_text_files |
| [verify_clean_game_duet.py](verify_clean_game_duet.py) | Read-only independent audit of the pinned v7 character-material refinement. | 未检出上述关键字；仍需读源码 |
| [verify_duet_caption_targets.py](verify_duet_caption_targets.py) | Read-only, static v6-to-v7 audit of a caption-only Cryptomatte target fix. | 未检出上述关键字；仍需读源码 |
| [verify_duet_integration.py](verify_duet_integration.py) | Compare both baked skeletons and authored camera across the time transform. | writes_text_files |
| [verify_gallery.py](verify_gallery.py) | Exercise the delivered gallery through a fresh, headless system Chrome. | writes_text_files |
| [verify_goo_eye_hair_stage.py](verify_goo_eye_hair_stage.py) | Reopen and verify bounded eye geometry, preserved motion and saved shader routes. | native_render_call, writes_text_files |
| [verify_goo_tyndall_master.py](verify_goo_tyndall_master.py) | Independently reopen the master and compare original motion/geometry, never video QA. | 未检出上述关键字；仍需读源码 |
| [verify_goo_window_wrap.py](verify_goo_window_wrap.py) | Independently reopen the saved window-wrap master; no output-video QA. | 未检出上述关键字；仍需读源码 |
| [verify_hesperides_reference.py](verify_hesperides_reference.py) | Reopen the independent hall study, verify switches/packing, and re-render. | native_render_call, writes_text_files |
| [verify_ikhor_sleeve_repair.py](verify_ikhor_sleeve_repair.py) | Read-only delta audit: v4 versus eight sleeve bones and one fixed corrective. | 未检出上述关键字；仍需读源码 |
| [verify_ikhor_wedding.py](verify_ikhor_wedding.py) | Independently reopen the bounded Aksiniya/Ikhor integration; never render/save. | 未检出上述关键字；仍需读源码 |
| [verify_light_space_repairs.py](verify_light_space_repairs.py) | Native regression check of reusable head-axis and stage-import repairs. | writes_text_files |
| [verify_linear_archive.py](verify_linear_archive.py) | Verify numbered multipart EXRs and independently decode their color data. | starts_external_process, writes_text_files |
| [verify_portrait_relight.py](verify_portrait_relight.py) | Read-only CPU reopen audit of a Clean-v2 portrait-relight still project. | writes_text_files |
| [verify_reference_transfer.py](verify_reference_transfer.py) | Independently reopen and audit the bounded reference transfer; never render/save. | 未检出上述关键字；仍需读源码 |
| [verify_render_seams.py](verify_render_seams.py) | Inspect decoded frames around known render boundaries for visible jumps. | writes_text_files |
| [verify_review_color.py](verify_review_color.py) | Require explicit decoded SDR review metadata, including after audio muxing. | starts_external_process, writes_text_files |
| [verify_stageart_master.py](verify_stageart_master.py) | Reopen a stage-art master and verify motion, output isolation and ground scope. | writes_text_files |
| [verify_video.py](verify_video.py) | Decode every output frame; verify timing, image dimensions, and MP4 streams. | writes_text_files |

## 资料读取与比较（21）

| 文件 | 模块说明 | 静态提示 |
| --- | --- | --- |
| [cache_mme_study_text.py](cache_mme_study_text.py) | Privately decode author archive text; do not execute or redistribute effects. | writes_text_files |
| [compare_look_frames.py](compare_look_frames.py) | Create an unretouched same-pose look comparison and a scene QA contact sheet. | 未检出上述关键字；仍需读源码 |
| [compare_mme_actor_stills.py](compare_mme_actor_stills.py) | Build labelled equal-camera crops from our rendered stills for visual review. | writes_text_files |
| [create_studio_fixture.py](create_studio_fixture.py) | Build original two-rig static test fixtures, not production MMD characters. | saves_blend, writes_text_files |
| [extract_tutorial_overlays.py](extract_tutorial_overlays.py) | Read colored on-screen annotations from a local tutorial at sampled times. | writes_text_files |
| [fetch_public_bilibili_study.py](fetch_public_bilibili_study.py) | Retrieve normally accessible public tutorial metadata/media for private study. | writes_text_files |
| [study_cinema_reference.py](study_cinema_reference.py) | Extract targeted full frames and consecutive bursts from a supplied reference. | writes_text_files |
| [study_citlali_fringe_shadow.py](study_citlali_fringe_shadow.py) | Still-only narrow warm hair contact-shadow study from the supplied reference. | native_render_call, saves_blend, writes_text_files |
| [study_goo_basic_light_groups.py](study_goo_basic_light_groups.py) | Test the basic one-key-per-group rule in isolated spheres, not production. | native_render_call, saves_blend, writes_text_files |
| [study_goo_color_basics.py](study_goo_color_basics.py) | Save fixed linear patches through existing Goo display transforms, without rendering. | writes_text_files |
| [study_goo_daylight_v2.py](study_goo_daylight_v2.py) | Render the saved v2 opening frame and a full-body lighting diagnostic. | native_render_call |
| [study_goo_feature_mechanisms.py](study_goo_feature_mechanisms.py) | Isolated Goo mechanism experiments; never load or edit a production project. | native_render_call, saves_blend, writes_text_files |
| [study_goo_info_input_matrix.py](study_goo_info_input_matrix.py) | Compare actual Shader Info inputs across existing Goo builds in empty scenes. | native_render_call, saves_blend, writes_text_files |
| [study_goo_mesh_normal_foundations.py](study_goo_mesh_normal_foundations.py) | Bounded Blender/Goo foundation controls in factory scenes; never load production. | native_render_call, saves_blend, writes_text_files |
| [study_goo_nodes.py](study_goo_nodes.py) | Render a small actual Goo shader/light-group study, separate from production. | native_render_call, saves_blend, writes_text_files |
| [study_goo_normal_input_basics.py](study_goo_normal_input_basics.py) | Check Shader Info Normal input against explicit normal-dot-light controls. | native_render_call, saves_blend, writes_text_files |
| [study_goo_window_visibility.py](study_goo_window_visibility.py) | Diagnose actual exterior-sun visibility on the saved floor only; never save. | native_render_call |
| [study_jelly_eye_inputs.py](study_jelly_eye_inputs.py) | Inventory the saved duet's eye geometry and shading without modifying it. | writes_text_files |
| [study_reference_sequences.py](study_reference_sequences.py) | Sample multi-second reference sequences for temporal art-direction review. | writes_text_files |
| [transcribe_tutorial.py](transcribe_tutorial.py) | Create a private, timestamped ASR study draft from local tutorial media. | starts_external_process, writes_text_files |
| [video_reference_frames.py](video_reference_frames.py) | Extract timestamped local reference frames and a contact sheet (OpenCV/Pillow). | writes_text_files |

## 其他工具与库模块（105）

| 文件 | 模块说明 | 静态提示 |
| --- | --- | --- |
| [__init__.py](__init__.py) | Local command-line helpers for blender-mmd-codex. | 未检出上述关键字；仍需读源码 |
| [aether_look_revision.py](aether_look_revision.py) | Rebuild Aether's own face, eyes, hair and masked outfit surfaces. | native_render_call, saves_blend, writes_text_files |
| [aether_material_audit.py](aether_material_audit.py) | Inspect Aether's actual source materials and export supplied packed textures. | writes_text_files |
| [align_caption_audio.py](align_caption_audio.py) | Measure a typography video's audio offset against the selected original BGM. | starts_external_process, writes_text_files |
| [align_duet_audio.py](align_duet_audio.py) | Estimate the MV-intro offset from original vocal/inst audio and VMD mouth tracks. | starts_external_process |
| [align_typography.py](align_typography.py) | Estimate a typography excerpt's origin in a longer typography video. | starts_external_process |
| [bake_goo_face_hair_shadows.py](bake_goo_face_hair_shadows.py) | Bake the two actors' actual animated bang occlusion to portable face-UV sequences. | saves_blend, writes_text_files |
| [benchmark_bold_wedding.py](benchmark_bold_wedding.py) | Unsaved 1080p benchmark of constant-one palette bypass pruning only. | native_render_call |
| [blender_bootstrap.py](blender_bootstrap.py) | Coordinate Blender detection, verified portable installation, and validation. | 未检出上述关键字；仍需读源码 |
| [blender_detect.py](blender_detect.py) | Detect installed Blender executables without modifying the host system. | 未检出上述关键字；仍需读源码 |
| [blender_download.py](blender_download.py) | Build official Blender release URLs and download files with SHA-256 verification. | 未检出上述关键字；仍需读源码 |
| [blender_install.py](blender_install.py) | Install Blender portable archives with path-traversal protection. | 未检出上述关键字；仍需读源码 |
| [blender_inventory.py](blender_inventory.py) | Read installed/enabled MMD add-ons and registered APIs inside Blender. | 未检出上述关键字；仍需读源码 |
| [blender_scene_audit.py](blender_scene_audit.py) | Inspect a supplied scene without executing embedded scripts or saving it. | writes_text_files |
| [blender_validate.py](blender_validate.py) | Validate Blender, its Python API, and optionally this project's Add-on. | 未检出上述关键字；仍需读源码 |
| [bold_wedding_materials.py](bold_wedding_materials.py) | Selective HDR motifs and narrow directional edges for Reference Transfer v3. | 未检出上述关键字；仍需读源码 |
| [bowlroll_public_download.py](bowlroll_public_download.py) | Download an author-published BowlRoll package only when open and password-free. | writes_text_files |
| [build_gallery.py](build_gallery.py) | Build the offline MMD Atlas from curated metadata and real local renders. | starts_external_process, writes_text_files, references_current_state |
| [build_goo_duet_sdf.py](build_goo_duet_sdf.py) | Pinned duet face-SDF adaptation; isolated stills, no motion or physics edits. | saves_blend, writes_text_files |
| [clean_aksiniya_materials.py](clean_aksiniya_materials.py) | Four reversible Aksiniya material modules for the pinned caption-fixed v7. | 未检出上述关键字；仍需读源码 |
| [clean_ikhor_materials.py](clean_ikhor_materials.py) | Four reversible Ikhor-only NPR refinements for an unsaved pinned v7. | 未检出上述关键字；仍需读源码 |
| [composite_duet_official_captions.py](composite_duet_official_captions.py) | Composite official caption groups onto native duet beauty/matte caches. | starts_external_process, writes_text_files |
| [configure_goo_portable.py](configure_goo_portable.py) | Save only the dedicated Goo preferences, after a factory-startup bootstrap. | saves_blend |
| [duet_engine_benchmark.py](duet_engine_benchmark.py) | Measure full-frame EEVEE variants without changing animation or source file. | native_render_call, writes_text_files |
| [duet_render_benchmark.py](duet_render_benchmark.py) | Measure full-resolution animation cost before the full-song render. | native_render_call, saves_blend, writes_text_files |
| [duet_source_preflight.py](duet_source_preflight.py) | Read duet source data using the installed MMD Tools PMX/VMD readers. | 未检出上述关键字；仍需读源码 |
| [export_linear_pipeline.py](export_linear_pipeline.py) | Validate native RGBA layers, a signed interaction pass and linear archives. | native_render_call, saves_blend, writes_text_files |
| [fit_reference_camera.py](fit_reference_camera.py) | Match architectural texture features and estimate a research camera pose. | writes_text_files |
| [fit_stage_grade.py](fit_stage_grade.py) | Fit global, monotonic RGB grading curves from a stage render and reference. | writes_text_files |
| [fix_goo_blended_eye_peek.py](fix_goo_blended_eye_peek.py) | Remove the failed dark eye-region result and test smooth alpha-blended bangs. | saves_blend, writes_text_files |
| [fix_goo_eye_peek_outline.py](fix_goo_eye_peek_outline.py) | Fade the MMD inverted-hull outline together with the eye-occluding hair. | saves_blend, writes_text_files |
| [fix_goo_eye_ray_and_shadow.py](fix_goo_eye_ray_and_shadow.py) | Use world-space camera rays for eye peek and observable NPR shadow controls. | saves_blend, writes_text_files |
| [fix_goo_window_shadow_pool.py](fix_goo_window_shadow_pool.py) | Increase the inherited full shadow pool; keep the revision's art graph unchanged. | native_render_call, saves_blend, writes_text_files |
| [frame_goo_window_shafts.py](frame_goo_window_shafts.py) | Frame the rear shafts and keep their real shadow dividers outside the camera. | native_render_call, saves_blend, writes_text_files |
| [genshin_material_adapt.py](genshin_material_adapt.py) | Adapt downloaded shader components to the duet's actual MMD inputs. | 未检出上述关键字；仍需读源码 |
| [goo_runtime.py](goo_runtime.py) | Initialize the isolated Goo 5.2 runtime, without changing global preferences. | 未检出上述关键字；仍需读源码 |
| [hesperides_camera_geometry.py](hesperides_camera_geometry.py) | Render textured geometry or ray-cast feature positions for reference fitting. | native_render_call, writes_text_files |
| [hesperides_reference_rebuild.py](hesperides_reference_rebuild.py) | Stage-only reconstruction of the supplied Ray preview; never run on a duet. | native_render_call, saves_blend, writes_text_files |
| [ikhor_character_materials.py](ikhor_character_materials.py) | Rebuild Ikhor's own NPR/material contract without touching motion or physics. | 未检出上述关键字；仍需读源码 |
| [ikhor_sleeve_repair_v1.py](ikhor_sleeve_repair_v1.py) | Diagnose and isolate Ikhor's sleeve bake without rebuilding the entire rig. | saves_blend |
| [ingest_bilibili_subtitles.py](ingest_bilibili_subtitles.py) | Normalize a legally saved Bilibili subtitle JSON, entirely offline. | 未检出上述关键字；仍需读源码 |
| [inventory_goo_basic_parameters.py](inventory_goo_basic_parameters.py) | Capture actual Goo node parameters in an empty process; never open production. | 未检出上述关键字；仍需读源码 |
| [inventory_goo_features.py](inventory_goo_features.py) | Inventory real shader RNA in an empty factory process, without loading production. | 未检出上述关键字；仍需读源码 |
| [make_aether_look_review.py](make_aether_look_review.py) | Arrange faithfully rendered before/after portraits for material review. | 未检出上述关键字；仍需读源码 |
| [make_aether_masks.py](make_aether_masks.py) | Derive reviewed, Aether-specific artistic controls from supplied textures. | writes_text_files |
| [make_clear_light_review.py](make_clear_light_review.py) | Compare true same-camera renders and measure actor/background brightness. | writes_text_files |
| [make_face_ink_review.py](make_face_ink_review.py) | Build aspect-preserving crops from reference and actual A/B renders. | writes_text_files |
| [make_portrait_quick_preview.py](make_portrait_quick_preview.py) | Produce only one captioned 1080p five-second review; skip post-output QA. | starts_external_process, writes_text_files, references_current_state |
| [make_surface_masks.py](make_surface_masks.py) | Create explicitly heuristic control maps from the model's actual atlases. | writes_text_files |
| [migrate_duet_to_blender53.py](migrate_duet_to_blender53.py) | Pinned Goo-to-native5.3 duet migration; audits and static-only conversion. | saves_blend, writes_text_files |
| [migrate_goo_wedding.py](migrate_goo_wedding.py) | Migrate the pinned daylight wedding to Goo, reusing the existing look and native Goo outputs. | native_render_call, saves_blend, writes_text_files |
| [mmd_camera_check.py](mmd_camera_check.py) | Import an authored camera VMD into an existing draft and audit sample frames. | native_render_call, saves_blend, writes_text_files |
| [mmd_caption_render.py](mmd_caption_render.py) | Render aspect-specific picture and Cryptomatte sequences for typography. | native_render_call, saves_blend, writes_text_files |
| [mmd_clear_light_revision.py](mmd_clear_light_revision.py) | Relight the selected hall and create a controlled SDR toon finish. | native_render_call, saves_blend, writes_text_files |
| [mmd_duet_finish.py](mmd_duet_finish.py) | Build the full-song duet from portable physics and the selected existing hall. | native_render_call, saves_blend, writes_text_files |
| [mmd_duet_physics.py](mmd_duet_physics.py) | Bake both performers' native physics for the full source choreography. | saves_blend, writes_text_files |
| [mmd_duet_polish.py](mmd_duet_polish.py) | Apply the user's brighter Ray-preview hall and Guanhaizi character direction. | native_render_call, saves_blend, writes_text_files |
| [mmd_face_ink.py](mmd_face_ink.py) | Selective facial strokes; source texture/UV/alpha and expression stay intact. | 未检出上述关键字；仍需读源码 |
| [mmd_final_scene.py](mmd_final_scene.py) | Art direct the physics-baked Aksiniya project with pastel stage and NPR materials. | native_render_call, saves_blend, writes_text_files |
| [mmd_first_scene.py](mmd_first_scene.py) | Create a new, explicitly labeled PMX + VMD import draft in Blender. | native_render_call, saves_blend |
| [mmd_half_lambert.py](mmd_half_lambert.py) | A named Half-Lambert response followed by per-material artistic gradients. | 未检出上述关键字；仍需读源码 |
| [mmd_hesperides_stage.py](mmd_hesperides_stage.py) | Adapt Hesperides' supplied Ray texture controls to Blender and render QA. | native_render_call, saves_blend, writes_text_files |
| [mmd_look_upgrade.py](mmd_look_upgrade.py) | Rebuild the Aksiniya look on a portable baked scene, preserving MMD layers. | native_render_call, saves_blend, writes_text_files |
| [mmd_outlines.py](mmd_outlines.py) | Readable MMD inverse-hull ink, retaining model edge/vertex weights. | native_render_call, saves_blend, writes_text_files |
| [mmd_physics_bake.py](mmd_physics_bake.py) | Build PMX rigid bodies, simulate sequentially, and export portable pose keys. | saves_blend, writes_text_files |
| [mmd_production_inspect.py](mmd_production_inspect.py) | Print production-relevant material, rig, and physics facts inside Blender. | 未检出上述关键字；仍需读源码 |
| [mmd_production_qa.py](mmd_production_qa.py) | Reopen verification and representative-frame QA for a baked production file. | native_render_call, writes_text_files |
| [mmd_quality_lab.py](mmd_quality_lab.py) | Isolate normal design, local AO, metallic trim and real volumetric light. | native_render_call, saves_blend, writes_text_files |
| [mmd_sample_pose.py](mmd_sample_pose.py) | Export selected evaluated bone matrices for before/after integration checks. | 未检出上述关键字；仍需读源码 |
| [mmd_style_apply.py](mmd_style_apply.py) | Apply a versioned NPR style to the validated local tutorial scene. | 未检出上述关键字；仍需读源码 |
| [mmd_surface_refine.py](mmd_surface_refine.py) | Model-adapted hair sheen, masked metal and restrained cloth/stage response. | native_render_call, saves_blend, writes_text_files |
| [mmd_tutorial_lab.py](mmd_tutorial_lab.py) | Validate selected toon-lighting, outline, glow and camera tutorial concepts. | native_render_call, saves_blend, writes_text_files |
| [native53_runtime.py](native53_runtime.py) | Register the isolated native5.3 MMD camera dependency before opening a project. | 未检出上述关键字；仍需读源码 |
| [ncm_convert.py](ncm_convert.py) | Convert local NCM files with ncmdump; preserve native FLAC/MP3 by default. | starts_external_process |
| [place_goo_window_air_inside_hall.py](place_goo_window_air_inside_hall.py) | Place actual scattering lights below the hall ceiling and remove volume linking ambiguity. | native_render_call, saves_blend, writes_text_files |
| [portrait_day_sky.py](portrait_day_sky.py) | Restore a blue/cyan procedural daytime World in the pinned duet copy. | 未检出上述关键字；仍需读源码 |
| [portrait_day_stage.py](portrait_day_stage.py) | Reversible daylight base for the two audited Hesperides duet files. | 未检出上述关键字；仍需读源码 |
| [portrait_fur_control.py](portrait_fur_control.py) | Original Normal/key fur palette on the pinned Clean v2 Aksiniya material. | 未检出上述关键字；仍需读源码 |
| [portrait_key_fill.py](portrait_key_fill.py) | Reversible portrait key/fill and single-palette experiment for Clean v2. | 未检出上述关键字；仍需读源码 |
| [portrait_rim_ink.py](portrait_rim_ink.py) | Reversible narrow warm rims and existing inverse-hull ink for Clean v2. | 未检出上述关键字；仍需读源码 |
| [quality_layer_capability.py](quality_layer_capability.py) | Small native EEVEE test for sky suppression and collection holdout. | native_render_call, writes_text_files |
| [raise_goo_toon_shadow_budget.py](raise_goo_toon_shadow_budget.py) | Increase only the inherited shadow memory budget and preflight peak frames. | native_render_call, saves_blend, writes_text_files |
| [read_goo_official_basics.py](read_goo_official_basics.py) | Cache selected official Goo source files privately for parameter study. | writes_text_files |
| [remove_wedding_arcs.py](remove_wedding_arcs.py) | Hide the two user-rejected wedding light arcs in a new saved revision. | saves_blend, writes_text_files |
| [reopen_goo_basic_light_groups.py](reopen_goo_basic_light_groups.py) | Independently reopen the basic experiment and compare its linear pixels. | native_render_call, writes_text_files |
| [reopen_goo_feature_study.py](reopen_goo_feature_study.py) | Reopen one isolated study blend and compare its linear render; no production input. | native_render_call |
| [review_face_ink.py](review_face_ink.py) | Same-camera face ink comparison and face-shell ablation renders. | native_render_call, saves_blend, writes_text_files |
| [review_hesperides_reference.py](review_hesperides_reference.py) | Package actual stage renders into labeled reference and switch comparisons. | writes_text_files |
| [review_hesperides_stage.py](review_hesperides_stage.py) | Create a labeled stage comparison and compare independent reopen renders. | writes_text_files |
| [review_ikhor_sleeve_controls.py](review_ikhor_sleeve_controls.py) | Render unsaved, unblurred wrist geometry controls with the production shader. | native_render_call, writes_text_files |
| [review_reference_transfer.py](review_reference_transfer.py) | Measure real native ablations and package same-frame comparison images. | 未检出上述关键字；仍需读源码 |
| [review_shader_diagnostics.py](review_shader_diagnostics.py) | Create visual inspection sheets and motion-compensated face-change metrics. | writes_text_files |
| [review_style_presets.py](review_style_presets.py) | Build same-pose style matrices from actual Blender beauty/matte outputs. | writes_text_files |
| [review_tutorial_study.py](review_tutorial_study.py) | Decode the four-second tutorial study and lay out unretouched comparisons. | writes_text_files |
| [review_video_color.py](review_video_color.py) | Explicit SDR desktop-review color contract for sRGB compositor pixels. | 未检出上述关键字；仍需读源码 |
| [revise_goo_projected_eye_shadow.py](revise_goo_projected_eye_shadow.py) | Correct eye peek in camera space and establish a directional head-light response. | saves_blend, writes_text_files |
| [revise_goo_rim_glow.py](revise_goo_rim_glow.py) | Inspect or revise the pinned Goo v2 light response in a new output directory. | native_render_call, saves_blend, writes_text_files |
| [stable_caption_layers.py](stable_caption_layers.py) | Whole-group caption compositing with explicit layer order and continuous masks. | 未检出上述关键字；仍需读源码 |
| [stage_night_art_lab.py](stage_night_art_lab.py) | Test moonlight, localized warmth and thin volume on a separate duet copy. | native_render_call, saves_blend, writes_text_files |
| [style_post.py](style_post.py) | Aspect-aware graphic post effects using real Blender character mattes. | 未检出上述关键字；仍需读源码 |
| [style_presets.py](style_presets.py) | Load independent render, post and aspect-specific direction recipes. | 未检出上述关键字；仍需读源码 |
| [transfer_material_response.py](transfer_material_response.py) | Opt-in material controls for the audited Character Layers production-v2. | 未检出上述关键字；仍需读源码 |
| [typography_composite.py](typography_composite.py) | Composite native-aspect typography with cue-specific front/back placement. | starts_external_process, writes_text_files |
| [validate_chest_secondary_motion.py](validate_chest_secondary_motion.py) | Audit anatomical chest support in source PMX and current baked motion. | writes_text_files |
| [wuwa_hair_input_lab.py](wuwa_hair_input_lab.py) | Render the user's WuWa hair example and controlled HM/HN input removals. | native_render_call, saves_blend, writes_text_files |
