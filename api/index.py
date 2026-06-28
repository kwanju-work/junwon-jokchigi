import os
import random
import json
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import httpx
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="준원이 족치기 API")

# Enable CORS for local testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Profile data
JUNWON_PROFILE = {
    "systemPrompt": """너는 '준원이'라는 캐릭터의 행동을 시나리오로 생성하는 AI야.

## 준원이 캐릭터 설정
- 20대 후반~30대 초반 남성
- 징징대고, 말 많고, 게임할 때 화 많고, 친구한테 시비 잘 거는 친구
- 하지만 근본적으로는 나쁜 사람이 아닌 애교 있는 캐릭터

## 말투 특징
- 한 문장을 여러 줄로 끊어서 말함
- 'ㅋ'를 10~30개씩 폭격
- 축약어 자주 사용: ㅈㄴ, ㅅㅂ, ㄹㅇ 등
- 경상도 사투리 섞임: ~노, ~하농, ~이고
- 영어를 한국식으로 변형: Cex, 뻐킹, 마더뻐킹
- 특유 표현: 개 푸씨, 걸레벌레, 맛도리, 지린다

## 행동 카테고리 (가족 관련 제외!)
1. 🎮 게임 분노: 피파/옵치에서 현질, 판정 불만, 급발진
2. 😤 직장 불만: 후배 불만, 일 없음/많음, 퇴근 욕구
3. 🤬 욕설 배틀: 친구한테 시비, 급발진, 별명 놀리기
4. 😢 징징/투정: 배고픔, 피곤함, 심심함 호소

## 중요 규칙
- 가족 관련 시나리오는 절대 생성하지 마
- 시나리오는 재미있고 과장된 톤으로
- 준원이의 대사는 위 말투를 충실히 반영해
- 상황 설명과 준원이의 대사를 모두 포함해""",

    "evaluationPrompt": """너는 '준원이 족치기' 게임의 심판 AI야.
사용자가 준원이의 문제 행동에 대해 어떻게 대응/훈육할지 답변했어.

## 평가 기준
1. **적절성 (30점)**: 상황에 맞는 적절한 대응인가?
2. **교육성 (25점)**: 준원이가 반성하고 배울 수 있는 방법인가?
3. **유머 (20점)**: 재미있고 위트 있는 대응인가?
4. **창의성 (15점)**: 독창적이고 참신한 방법인가?
5. **실현가능성 (10점)**: 현실적으로 가능한 방법인가?

## 등급 기준
- S (90-100): 족치기 마스터 - 준원이가 울면서 반성함
- A (80-89): 족치기 고수 - 준원이가 조용해짐
- B (70-79): 나름 괜찮은 족치기 - 준원이가 잠시 멈춤
- C (60-69): 미흡한 족치기 - 준원이가 되려 반격함
- D (50-59): 약한 족치기 - 준원이가 무시함
- F (0-49): 실패 - 준원이가 더 날뜀

## 응답 형식
반드시 아래 JSON 형식으로만 응답해. 다른 텍스트 없이 JSON만:
{
  "score": 숫자(0-100),
  "grade": "S/A/B/C/D/F",
  "title": "칭호",
  "feedback": "전체 피드백 (2-3문장, 재미있게)",
  "good": "잘한 점 (1-2문장)",
  "improve": "개선할 점 (1-2문장)",
  "tip": "프로 팁 (1문장)"
}"""
}

CATEGORIES = [
    {
        "id": "game", "name": "게임 분노", "emoji": "🎮",
        "description": "피파(FC온라인)/옵치에서 현질하고, 판정에 화내고, 게임 실력 자랑하는 상황",
        "triggers": ["현질 고민", "선수카드 강화 실패", "상대방 판정 불만", "팀원 못함", "게임 중 급발진", "상대방에게 지고 화냄"],
        "examples": [
            "아 ㅅㅂ 이게 왜 안들어가!! 판정 개같네 진짜",
            "ㅋㅋㅋㅋㅋㅋ 야 나 이영표 8카 샀어 1조주고 너네 바지 갈아입을준비해",
            "씨발럼들 왜이러노 이게 정상이냐 ㅋㅋㅋㅋ",
            "시그마 나오면 섭딜이 해줘 메타임 알겠어?",
            "아 존나웃기네 ㅋㅋㅋㅋㅋ 구라치지마 안당해",
            "옵치 마렵다 마렵다 마렵다",
            "혼자 겜처하는거 개꼴받네"
        ]
    },
    {
        "id": "work", "name": "직장 불만", "emoji": "😤",
        "description": "직장에서 후배/동료에 대한 불만, 일 안하고 싶음, 퇴근하고 싶음",
        "triggers": ["후배가 까불때", "일이 없을때", "일이 너무 많을때", "퇴근하고 싶을때", "사원이 판단을 혼자 할때"],
        "examples": [
            "진짜 사원새끼가 왜케 존나까불지 병신이 판단을 지혼자함",
            "할일이 없어서 오늘 ㄹㅇ 큰일 하루종일 자도 누가 뭐라 안하겠노",
            "나는 너무 한가해 그냥 지금 집가고싶오",
            "아 벌써부터 일없어 피파할래? ㅋㅋㅋㅋㅋ",
            "오늘 12시간 강의 개에반데",
            "아오 ㅅㅂ 개피곤하농 진짜"
        ]
    },
    {
        "id": "cursing", "name": "욕설 배틀", "emoji": "🤬",
        "description": "친구한테 시비걸고, 급발진하고, 별명 부르고 욕설 핑퐁",
        "triggers": ["친구가 놀렸을때", "별명 불렸을때", "무시당했을때", "갑자기 급발진", "친구가 안놀아줄때"],
        "examples": [
            "류씨벌련아 언제와",
            "개 푸씨잖아 ㅋㅋㅋㅋㅋ 도라이같은련 푸씨같은련",
            "급발진 포인트가 존나 독특한 색기",
            "누구보고 병신들이래 ㅋㅋㅋㅋㅋ 걸레벌레가",
            "야야 금 넘어오지마 선 넘어오지마!",
            "너? 개 푸씨 잖아 ㅋㅋㅋㅋ",
            "함 해줘? 함 해줘? 함 해줘?"
        ]
    },
    {
        "id": "whining", "name": "징징/투정", "emoji": "😢",
        "description": "피곤함, 배고픔, 심심함을 호소하며 징징대는 상황",
        "triggers": ["배고플때", "피곤할때", "심심할때", "누가 안놀아줄때", "뭔가 조를때"],
        "examples": [
            "아이 배고파 씨벌거 ㅋㅋㅋㅋ",
            "어우시 ㅋㅋㅋㅋ 진짜 하루하루 지린다이거",
            "왜 나랑보고싶었어? ㅠㅠ",
            "어디가 어디가 어디가 커피들고 어디가",
            "함 해줘? 함 해줘? 함 해줘?",
            "관주야 너 좀 천천히와 좀 제발!",
            "부럽노.."
        ]
    }
]

async def call_gemini(system_prompt: str, user_message: str, response_mime_type: str = "text/plain") -> str:
    if not GEMINI_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="서버에 GEMINI_API_KEY가 설정되지 않았습니다. .env 파일을 확인하거나 환경 변수를 설정해주세요."
        )
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "system_instruction": {
            "parts": [{"text": system_prompt}]
        },
        "contents": [{
            "role": "user",
            "parts": [{"text": user_message}]
        }],
        "generationConfig": {
            "temperature": 1.0,
            "maxOutputTokens": 1024,
            "responseMimeType": response_mime_type,
        }
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=payload)
        if response.status_code != 200:
            try:
                err_data = response.json()
                msg = err_data.get("error", {}).get("message", "Unknown Gemini API error")
            except:
                msg = response.text
            raise HTTPException(status_code=502, detail=f"Gemini API Error: {msg}")
        
        data = response.json()
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError):
            raise HTTPException(status_code=502, detail="Invalid response structure from Gemini API")

@app.post("/api/generate")
async def generate_scenario(body: dict = Body(...)):
    category_id = body.get("category")
    kakao_samples = body.get("kakaoSamples", [])
    
    # Select category
    if category_id:
        category = next((c for c in CATEGORIES if c["id"] == category_id), None)
    else:
        category = None
        
    if not category:
        category = random.choice(CATEGORIES)
        
    extra_context = ""
    if kakao_samples:
        shuffled = list(kakao_samples)
        random.shuffle(shuffled)
        samples = shuffled[:10]
        extra_context = f"\n\n실제 카카오톡 대화에서 추출한 준원이 발언 참고:\n" + "\n".join(f"- \"{s}\"" for s in samples)
        
    user_prompt = f"""다음 카테고리에 맞는 준원이의 문제 행동 시나리오를 하나 생성해줘.

카테고리: {category['emoji']} {category['name']}
설명: {category['description']}
트리거 예시: {', '.join(category['triggers'])}

참고 대사 예시:
{chr(10).join(f'- "{d}"' for d in category['examples'])}
{extra_context}

아래 JSON 형식으로 응답해. JSON만, 다른 텍스트 없이:
{{
  "situation": "상황 설명 (2-3문장, 어떤 상황인지 재미있게 묘사)",
  "dialogue": ["준원이의 대사1", "대사2", "대사3"] (3-6개의 메시지, 끊어치기 스타일로)
}}"""

    result_text = await call_gemini(JUNWON_PROFILE["systemPrompt"], user_prompt, response_mime_type="application/json")
    
    # Parse JSON from Gemini response
    try:
        parsed = json.loads(result_text)
    except:
        # Fallback search for JSON structure
        import re
        json_match = re.search(r'\{[\s\S]*\}', result_text)
        if json_match:
            try:
                parsed = json.loads(json_match.group(0))
            except:
                raise HTTPException(status_code=502, detail="Failed to parse JSON response from AI model")
        else:
            raise HTTPException(status_code=502, detail="AI model did not return a valid JSON format")
            
    return {
        "category": category["id"],
        "categoryName": category["name"],
        "categoryEmoji": category["emoji"],
        "situation": parsed.get("situation", ""),
        "dialogue": parsed.get("dialogue", [])
    }

@app.post("/api/evaluate")
async def evaluate_answer(body: dict = Body(...)):
    scenario = body.get("scenario")
    user_answer = body.get("userAnswer")
    
    if not scenario or not user_answer:
        raise HTTPException(status_code=400, detail="Missing scenario or userAnswer in request body")
        
    user_prompt = f"""## 시나리오
상황: {scenario.get('situation', '')}
준원이 대사: {chr(10).join(f'{i+1}. "{d}"' for i, d in enumerate(scenario.get('dialogue', [])))}
카테고리: {scenario.get('categoryEmoji', '')} {scenario.get('categoryName', '')}

## 사용자의 대응
"{user_answer}"

위 기준에 따라 사용자의 대응을 평가해줘. JSON으로만 응답해."""

    result_text = await call_gemini(JUNWON_PROFILE["evaluationPrompt"], user_prompt, response_mime_type="application/json")
    
    try:
        parsed = json.loads(result_text)
    except:
        import re
        json_match = re.search(r'\{[\s\S]*\}', result_text)
        if json_match:
            try:
                parsed = json.loads(json_match.group(0))
            except:
                raise HTTPException(status_code=502, detail="Failed to parse evaluation JSON from AI model")
        else:
            raise HTTPException(status_code=502, detail="AI model did not return a valid evaluation JSON")
            
    return parsed

# Serve static frontend files
@app.get("/")
async def serve_home():
    path = os.path.join("public", "index.html")
    if os.path.exists(path):
        return FileResponse(path)
    return HTMLResponse("<h1>준원이 족치기 프론트엔드 파일(public/index.html)이 없습니다.</h1>")

@app.get("/{filename}")
async def serve_static(filename: str):
    path = os.path.join("public", filename)
    if os.path.exists(path):
        return FileResponse(path)
    # Fallback to index if route doesn't match a file
    index_path = os.path.join("public", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    raise HTTPException(status_code=404, detail="File not found")

if __name__ == "__main__":
    import uvicorn
    # Local dev server runs on port 8000
    uvicorn.run("index:app", host="127.0.0.1", port=8000, reload=True)
