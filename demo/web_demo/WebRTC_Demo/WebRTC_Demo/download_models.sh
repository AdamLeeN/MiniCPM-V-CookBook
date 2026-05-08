#!/bin/bash
# ============================================================
# MiniCPM-o 4.5 GGUF Model Download Script
# Downloads all required GGUF model files for the WebRTC demo
#
# Supports: HuggingFace (hf) and ModelScope (ms)
# Auto-detects the faster source if not specified
# ============================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ============================================================
# Configuration
# ============================================================
HF_REPO="openbmb/MiniCPM-o-4_5-gguf"
MS_REPO="openbmb/MiniCPM-o-4_5-gguf"

HF_BASE_URL="https://huggingface.co/${HF_REPO}/resolve/main"
MS_BASE_URL="https://modelscope.cn/models/${MS_REPO}/resolve/master"

# LLM quantization variant (default: Q4_K_M, can override via --quant)
LLM_QUANT="Q4_K_M"

# Output directory
MODEL_DIR=""

# Source: auto / hf / ms
SOURCE="auto"

# ============================================================
# Files to download
# ============================================================
# These are the required files for the WebRTC demo
# Format: "relative_path|description|approximate_size"
REQUIRED_FILES=(
    "LLM_PLACEHOLDER|LLM main model|~5GB"
    "audio/MiniCPM-o-4_5-audio-F16.gguf|Audio encoder|630MB"
    "vision/MiniCPM-o-4_5-vision-F16.gguf|Vision encoder|1.0GB"
    "tts/MiniCPM-o-4_5-tts-F16.gguf|TTS model|1.1GB"
    "tts/MiniCPM-o-4_5-projector-F16.gguf|TTS projector|14MB"
    "token2wav-gguf/encoder.gguf|Token2Wav encoder|144MB"
    "token2wav-gguf/flow_matching.gguf|Token2Wav flow matching|437MB"
    "token2wav-gguf/flow_extra.gguf|Token2Wav flow extra|13MB"
    "token2wav-gguf/hifigan2.gguf|Token2Wav vocoder|79MB"
    "token2wav-gguf/prompt_cache.gguf|Token2Wav prompt cache|202MB"
)

# ============================================================
# Parse arguments
# ============================================================
print_help() {
    echo -e "${BLUE}============================================${NC}"
    echo -e "${BLUE}  MiniCPM-o 4.5 GGUF Model Downloader${NC}"
    echo -e "${BLUE}============================================${NC}"
    echo ""
    echo "Usage: $0 --model-dir <path> [options]"
    echo ""
    echo "Required:"
    echo "  --model-dir PATH     Directory to save model files"
    echo ""
    echo "Options:"
    echo "  --source hf|ms|auto  Download source (default: auto)"
    echo "                       hf   = HuggingFace"
    echo "                       ms   = ModelScope (faster in China)"
    echo "                       auto = Test both and pick faster"
    echo "  --quant VARIANT      LLM quantization (default: Q4_K_M)"
    echo "                       Options: Q4_0, Q4_1, Q4_K_M, Q4_K_S,"
    echo "                                Q5_0, Q5_1, Q5_K_M, Q5_K_S,"
    echo "                                Q6_K, Q8_0, F16"
    echo "  --hf-mirror URL      Custom HuggingFace mirror URL"
    echo "  --help               Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 --model-dir ./gguf"
    echo "  $0 --model-dir ./gguf --source ms"
    echo "  $0 --model-dir ./gguf --quant Q8_0"
    echo "  $0 --model-dir ./gguf --hf-mirror https://hf-mirror.com"
}

HF_MIRROR=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --model-dir)
            MODEL_DIR="$2"; shift 2 ;;
        --source)
            SOURCE="$2"; shift 2 ;;
        --quant)
            LLM_QUANT="$2"; shift 2 ;;
        --hf-mirror)
            HF_MIRROR="$2"; shift 2 ;;
        --help|-h)
            print_help; exit 0 ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"; print_help; exit 1 ;;
    esac
done

if [ -z "$MODEL_DIR" ]; then
    echo -e "${RED}Error: --model-dir is required${NC}"
    echo ""
    print_help
    exit 1
fi

# Apply HF mirror if specified
if [ -n "$HF_MIRROR" ]; then
    HF_BASE_URL="${HF_MIRROR}/${HF_REPO}/resolve/main"
    echo -e "${YELLOW}Using HuggingFace mirror: ${HF_MIRROR}${NC}"
fi

# Replace LLM placeholder with actual filename
LLM_FILE="MiniCPM-o-4_5-${LLM_QUANT}.gguf"

# ============================================================
# Speed test function
# ============================================================
test_speed() {
    local url="$1"
    local name="$2"
    
    # Download first 1MB and measure time
    local start_time=$(date +%s%N 2>/dev/null || python3 -c "import time; print(int(time.time()*1e9))")
    local http_code
    http_code=$(curl -sL -o /dev/null -w "%{http_code}" --max-time 10 --range 0-1048575 "$url" 2>/dev/null)
    local end_time=$(date +%s%N 2>/dev/null || python3 -c "import time; print(int(time.time()*1e9))")
    
    if [ "$http_code" != "200" ] && [ "$http_code" != "206" ]; then
        echo -e "  ${name}: ${RED}Failed (HTTP ${http_code})${NC}"
        echo "0"
        return
    fi
    
    local elapsed_ms=$(( (end_time - start_time) / 1000000 ))
    if [ "$elapsed_ms" -le 0 ]; then elapsed_ms=1; fi
    local speed_kbps=$(( 1024 * 1000 / elapsed_ms ))
    
    echo -e "  ${name}: ${GREEN}${speed_kbps} KB/s${NC} (${elapsed_ms}ms for 1MB)" >&2
    echo "$speed_kbps"
}

# ============================================================
# Select download source
# ============================================================
select_source() {
    if [ "$SOURCE" != "auto" ]; then
        echo -e "${GREEN}Using source: ${SOURCE}${NC}"
        return
    fi
    
    echo -e "${YELLOW}Testing download speed...${NC}"
    
    # Use a small file for speed test
    local test_file="token2wav-gguf/flow_extra.gguf"
    local hf_url="${HF_BASE_URL}/${test_file}"
    local ms_url="${MS_BASE_URL}/${test_file}"
    
    local hf_speed=$(test_speed "$hf_url" "HuggingFace")
    local ms_speed=$(test_speed "$ms_url" "ModelScope")
    
    if [ "$hf_speed" -gt "$ms_speed" ] 2>/dev/null; then
        SOURCE="hf"
        echo -e "${GREEN}Selected: HuggingFace (faster)${NC}"
    elif [ "$ms_speed" -gt 0 ] 2>/dev/null; then
        SOURCE="ms"
        echo -e "${GREEN}Selected: ModelScope (faster)${NC}"
    else
        SOURCE="hf"
        echo -e "${YELLOW}Defaulting to HuggingFace${NC}"
    fi
    echo ""
}

# ============================================================
# Download function
# ============================================================
download_file() {
    local relative_path="$1"
    local description="$2"
    local approx_size="$3"
    
    local target_path="${MODEL_DIR}/${relative_path}"
    local target_dir=$(dirname "$target_path")
    
    # Skip if already exists
    if [ -f "$target_path" ]; then
        local file_size=$(ls -lh "$target_path" 2>/dev/null | awk '{print $5}')
        echo -e "  ${GREEN}✅ Skip${NC} ${relative_path} (exists, ${file_size})"
        return 0
    fi
    
    # Create directory
    mkdir -p "$target_dir"
    
    # Build URL
    local url
    if [ "$SOURCE" == "ms" ]; then
        url="${MS_BASE_URL}/${relative_path}"
    else
        url="${HF_BASE_URL}/${relative_path}"
    fi
    
    echo -e "  ${BLUE}⬇️  Downloading${NC} ${relative_path} (${description}, ${approx_size})"
    
    # Download with progress bar and resume support
    if curl -L -C - --progress-bar -o "$target_path" "$url"; then
        local file_size=$(ls -lh "$target_path" 2>/dev/null | awk '{print $5}')
        echo -e "  ${GREEN}✅ Done${NC} ${relative_path} (${file_size})"
    else
        echo -e "  ${RED}❌ Failed${NC} ${relative_path}"
        rm -f "$target_path"
        return 1
    fi
}

# ============================================================
# Main
# ============================================================
echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}  MiniCPM-o 4.5 GGUF Model Downloader${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""
echo -e "  Model dir:  ${GREEN}${MODEL_DIR}${NC}"
echo -e "  LLM quant:  ${GREEN}${LLM_QUANT}${NC}"
echo -e "  LLM file:   ${GREEN}${LLM_FILE}${NC}"
echo ""

# Select source
select_source

echo -e "${YELLOW}Downloading model files from ${SOURCE}...${NC}"
echo ""

# Create base directory
mkdir -p "$MODEL_DIR"

FAILED=0
TOTAL=${#REQUIRED_FILES[@]}
DOWNLOADED=0

for entry in "${REQUIRED_FILES[@]}"; do
    IFS='|' read -r rel_path desc size <<< "$entry"
    
    # Replace LLM placeholder
    if [ "$rel_path" == "LLM_PLACEHOLDER" ]; then
        rel_path="$LLM_FILE"
    fi
    
    if download_file "$rel_path" "$desc" "$size"; then
        DOWNLOADED=$((DOWNLOADED + 1))
    else
        FAILED=$((FAILED + 1))
    fi
done

echo ""
echo -e "${BLUE}============================================${NC}"
if [ "$FAILED" -eq 0 ]; then
    echo -e "${GREEN}✅ All ${TOTAL} files ready!${NC}"
else
    echo -e "${YELLOW}⚠️  ${DOWNLOADED}/${TOTAL} files ready, ${FAILED} failed${NC}"
    echo -e "${YELLOW}   Re-run the script to retry failed downloads (supports resume)${NC}"
fi
echo ""
echo -e "  Model directory: ${GREEN}${MODEL_DIR}${NC}"
echo ""

# Verify directory structure
echo -e "${YELLOW}Verifying model files...${NC}"
MISSING=0
for entry in "${REQUIRED_FILES[@]}"; do
    IFS='|' read -r rel_path desc size <<< "$entry"
    if [ "$rel_path" == "LLM_PLACEHOLDER" ]; then
        rel_path="$LLM_FILE"
    fi
    if [ ! -f "${MODEL_DIR}/${rel_path}" ]; then
        echo -e "  ${RED}❌ Missing: ${rel_path}${NC}"
        MISSING=$((MISSING + 1))
    fi
done

if [ "$MISSING" -eq 0 ]; then
    echo -e "  ${GREEN}✅ All model files verified!${NC}"
    echo ""
    echo -e "${GREEN}You can now deploy with:${NC}"
    echo "  ./deploy_all.sh --cpp-dir /path/to/llama.cpp-omni --model-dir ${MODEL_DIR}"
else
    echo -e "  ${RED}${MISSING} file(s) missing. Please re-run the script.${NC}"
fi
echo -e "${BLUE}============================================${NC}"
