param(
    [Parameter(Mandatory = $true)][string]$OutputRoot,
    [string]$CacheRoot = 'D:\codex\temp\mmd-style-suite-new',
    [string]$SourceProject = 'D:\codex\output\MMD-Tutorial-Study-v1\tutorial-study.blend',
    [string]$Blender = 'E:\tools\Blender Foundation\Blender 5.2\blender.exe',
    [string]$FFmpeg = 'D:\codex\temp\blender-mmd-video-tools\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe',
    [string[]]$PackageIds = @('gosari-portrait-v1', 'gosari-landscape-v1', 'guanhaizi-graphic-portrait-v1', 'guanhaizi-graphic-landscape-v1', 'guanhaizi-neon-portrait-v1', 'guanhaizi-neon-landscape-v1'),
    [int]$Percentage = 50,
    [int]$Samples = 48,
    [switch]$Resume
)

# This reproducible lab intentionally uses the already checked source interval
# 421..660 at 60 fps. It is not a general camera/motion retargeting command.
$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
$repoRoot = Split-Path -Parent $PSScriptRoot
if ((Test-Path -LiteralPath $OutputRoot) -and -not $Resume) { throw 'Use a new output root or explicitly resume verified stages' }
if ((Test-Path -LiteralPath $CacheRoot) -and -not $Resume) { throw 'Use a new cache root or explicitly resume verified stages' }
foreach ($required in @($Blender, $FFmpeg, $SourceProject)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) { throw "Missing source/runtime: $required" }
}
New-Item -ItemType Directory -Path $OutputRoot -Force | Out-Null
New-Item -ItemType Directory -Path $CacheRoot -Force | Out-Null
$audioSource = Join-Path 'E:\tools\franken' ('FrankensteinNoKaibutsu_Audio_Inst' + [char]0xB1 + '0.wav')

function Invoke-Checked([string]$Program, [string[]]$ToolArgs, [string]$Log) {
    $priorPolicy = $ErrorActionPreference
    try {
        # Windows PowerShell 5 treats native stderr (including FFmpeg progress)
        # as an error record. Judge native success by its actual exit status.
        $ErrorActionPreference = 'Continue'
        & $Program @ToolArgs *> $Log
        $toolExit = $LASTEXITCODE
    } finally { $ErrorActionPreference = $priorPolicy }
    if ($toolExit -ne 0) {
        Get-Content -LiteralPath $Log -Tail 24
        throw "Stage failed; see $Log"
    }
}

Push-Location $repoRoot
try {
    foreach ($id in $PackageIds) {
        if ($id -notmatch '^[a-z0-9-]+$') { throw 'Invalid package id' }
        $package = Join-Path $repoRoot "presets\styles\packages\$id.json"
        $recipe = Get-Content -LiteralPath $package -Raw -Encoding UTF8 | ConvertFrom-Json
        $aspect = $recipe.aspect
        $target = Join-Path $OutputRoot $id
        New-Item -ItemType Directory -Path $target -Force | Out-Null
        $cache = Join-Path $CacheRoot $id
        $renderLog = Join-Path $CacheRoot "$id-render.log"
        Write-Output "STYLE_RENDER_BEGIN $id $(Get-Date -Format o)"
        $report = Join-Path $target 'scene\render-report.json'
        if ($Resume -and (Test-Path -LiteralPath $report)) {
            Invoke-Checked 'python' @('scripts/style_presets.py', '--package', $package, '--verify-render-report', $report, '--source-project', $SourceProject, '--percentage', "$Percentage", '--samples', "$Samples") (Join-Path $CacheRoot "$id-resume-check.log")
        } else {
            Invoke-Checked $Blender @('--background', $SourceProject, '--disable-autoexec', '--python-exit-code', '1', '--python', 'scripts/mmd_caption_render.py', '--', '--style-package', $package, '--aspect', $aspect, '--output-dir', (Join-Path $target 'scene'), '--cache-dir', $cache, '--percentage', "$Percentage", '--samples', "$Samples") $renderLog
        }
        Write-Output "STYLE_RENDER_DONE $id $(Get-Date -Format o)"
        $typography = if ($aspect -eq 'portrait') {
            'D:\codex\output\blender-mmd-codex\franken-caption-assets-v001\FrankensteinNoKaibutsu_Video_1Sabi_Typography(Tall).mp4'
        } else {
            'E:\tools\franken\FrankensteinNoKaibutsu_Video_Full_Typography(Wide).mp4'
        }
        $postReport = Join-Path $target 'composite\caption-verification.json'
        if ($Resume -and (Test-Path -LiteralPath $postReport)) {
            Invoke-Checked 'python' @('scripts/style_presets.py', '--package', $package, '--verify-post-report', $postReport) (Join-Path $CacheRoot "$id-post-resume-check.log")
        } else {
            Invoke-Checked 'python' @('scripts/typography_composite.py', '--cache-dir', $cache, '--typography', $typography, '--style-package', $package, '--ffmpeg', $FFmpeg, '--output-dir', (Join-Path $target 'composite')) (Join-Path $CacheRoot "$id-post.log")
        }
        $video = Join-Path $target "$id.mp4"
        if (-not ($Resume -and (Test-Path -LiteralPath $video))) {
            Invoke-Checked 'python' @('scripts/mux_production_audio.py', '--video', (Join-Path $target 'composite\typography-picture.mp4'), '--audio', $audioSource, '--output', $video, '--audio-start', '66.7666666667', '--seconds', '4', '--gain', '0.75', '--ffmpeg', $FFmpeg) (Join-Path $CacheRoot "$id-mux.log")
        }
        $width = if ($aspect -eq 'portrait') { [int](1080 * $Percentage / 100) } else { [int](1920 * $Percentage / 100) }
        $height = if ($aspect -eq 'portrait') { [int](1920 * $Percentage / 100) } else { [int](1080 * $Percentage / 100) }
        $qaDir = if ($Resume) { Join-Path $target ('video-qa-resume-' + (Get-Date -Format 'yyyyMMddHHmmss')) } else { Join-Path $target 'video-qa' }
        $audioQa = if ($Resume) { Join-Path $target ('audio-qa-resume-' + (Get-Date -Format 'yyyyMMddHHmmss') + '.json') } else { Join-Path $target 'audio-qa.json' }
        Invoke-Checked 'python' @('scripts/verify_video.py', '--video', $video, '--output-dir', $qaDir, '--width', "$width", '--height', "$height", '--fps', '60', '--seconds', '4') (Join-Path $CacheRoot "$id-video-qa.log")
        Invoke-Checked $Blender @('--background', '--factory-startup', '--disable-autoexec', '--python-exit-code', '1', '--python', 'scripts/verify_audio_blender.py', '--', '--video', $video, '--output', $audioQa, '--seconds', '4') (Join-Path $CacheRoot "$id-audio-qa.log")
        Write-Output "STYLE_CLIP_VERIFIED $id $(Get-Date -Format o)"
    }
} finally {
    Pop-Location
}
