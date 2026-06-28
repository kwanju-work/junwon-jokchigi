import os
import random
import json
import asyncio
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
- 징징대고, 친구한테 시비 잘 거는 친구
- 너무 공격적이거나 험악하게 욕설을 퍼붓기보다, 투정 부리고 징징대며 가벼운 비속어를 섞어 짜증 내는 톤
- 말수가 적고 대답을 짧고 간결하게 툭툭 던지는 스타일

## 말투 특징
- 한 문장을 3~4개의 매우 짧은 메시지로 끊어서 말함
- 'ㅋ'는 남발하지 말고 3~6개 정도로 줄여서 적절히 사용 (예: ㅋㅋㅋ)
- 축약어 가끔 사용: ㅈㄴ, ㅅㅂ, ㄹㅇ 등
- 경상도 사투리 섞임: ~노, ~하농, ~이고
- 영어를 한국식으로 변형: Cex, 뻐킹
- 특유 표현: 개 푸씨, 맛도리, 지린다

## 행동 카테고리 (가족 관련 제외!)
1. 🎮 게임 분노: 피파/옵치에서 현질, 판정 불만, 급발진
2. 😤 직장 불만: 후배 불만, 일 없음/많음, 퇴근 욕구
3. 🤬 욕설 배틀: 친구한테 시비, 급발진, 별명 놀리기
4. 😢 징징/투정: 배고픔, 피곤함, 심심함 호소

## 중요 규칙
- **생활 환경 전제조건**: 준원이와 사용자는 **각자 서로 다른 집에 따로 살고 있습니다.** 동거하거나 같은 방/같은 집 공간에 상주하고 있는 오프라인 상황은 절대 생성하지 마세요.
- **게임 환경 전제조건**: 게임 상황 묘사 시 PC방에서 같이 하거나 한 방에 있는 오프라인 상황이 아니라, **각자 본인 집에서 컴퓨터로 접속해 온라인(디스코드, 인게임 보이스, 카톡 등)으로 소통하며 멀티플레이를 하는 중**으로만 철저히 묘사하세요.
- 가족 관련 시나리오는 절대 생성하지 마
- 시나리오는 재미있고 생동감 있게
- 대사는 구질구질하게 길게 쓰지 말고, 짧고 간결하게 3~4줄로 툭툭 끊어 쳐
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
        "description": "오버워치에서 딜러(트레이서, 겐지, 맥크리 등)를 플레이하며 탱커와 힐러 탓을 심하게 하고 징징거리는 상황",
        "triggers": ["탱커가 진입 안할 때", "힐러가 힐 안줄 때", "본인은 딜금인데 질 때", "옵치 딜러 매칭 대기", "팀원 탓하며 급발진할 때"],
        "examples": [
            "아니 탱커새끼 뭐하노? 방벽 안 들고 뒤에서 탭댄스 추나 ㅋㅋㅋ",
            "힐 안 들어오는데 게임 어케하노 ㅋㅋㅋ 아나 뇌 빼고 겜함?",
            "나 딜 ㅈㄴ 우겨넣었는데 왜 지냐? 탱힐 ㄹㅇ 개벌레들이네",
            "아니 트레이서로 3뚝 다 따줬는데 이걸 지네 ㅋㅋㅋㅋ 개에반데",
            "힐러 진짜 역겹네 힐 줄 생각 없으면 딜러나 쳐해라 ㅈㄴ",
            "옵치 딜러 매칭 ㅈㄴ 안되네.. 탱힐 벌레들 버스 태우기 개피곤하농",
            "진짜 아군 탱커 던지냐? 시그마 픽하고 뒤에서 라면 처먹네"
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
            "maxOutputTokens": 8192,
            "responseMimeType": response_mime_type,
        }
    }
    
    max_retries = 3
    for attempt in range(max_retries):
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            if response.status_code == 200:
                data = response.json()
                try:
                    return data["candidates"][0]["content"]["parts"][0]["text"]
                except (KeyError, IndexError):
                    raise HTTPException(status_code=502, detail="Invalid response structure from Gemini API")
            
            # Retry on temporary errors (429 Rate Limit, 503 Service Unavailable)
            if response.status_code in [429, 503] and attempt < max_retries - 1:
                await asyncio.sleep(1.5 * (attempt + 1))
                continue
                
            try:
                err_data = response.json()
                msg = err_data.get("error", {}).get("message", "Unknown Gemini API error")
            except:
                msg = response.text
            raise HTTPException(status_code=response.status_code, detail=f"Gemini API Error: {msg}")

@app.post("/api/generate")
async def generate_scenario(body: dict = Body(...)):
    category_id = body.get("category")
    kakao_samples = body.get("kakaoSamples", [])
    player_name = body.get("playerName", "친구")
    
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
훈육자(사용자) 이름: {player_name}

참고 대사 예시:
{chr(10).join(f'- "{d}"' for d in category['examples'])}
{extra_context}

## 중요 규칙 (사용자 이름 반영):
- 사용자의 이름은 "{player_name}"이야. 준원이가 대사나 톡에서 사용자를 직접 호명할 때 친근하게 "{player_name}"(또는 "{player_name}야", "야", "너")이라고 부르는 대사를 대화창에 최소 1번 이상 포함시켜줘.

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
    player_name = body.get("playerName", "친구")
    
    if not scenario or not user_answer:
        raise HTTPException(status_code=400, detail="Missing scenario or userAnswer in request body")
        
    user_prompt = f"""## 시나리오
상황: {scenario.get('situation', '')}
준원이 대사: {chr(10).join(f'{i+1}. "{d}"' for i, d in enumerate(scenario.get('dialogue', [])))}
카테고리: {scenario.get('categoryEmoji', '')} {scenario.get('categoryName', '')}
사용자(훈육자) 이름: {player_name}

## 사용자의 대응
"{user_answer}"

위 시나리오 상황에서 사용자 {player_name}가 취한 대응을 기준에 따라 평가해줘. JSON으로만 응답해."""

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

@app.post("/api/report-solution")
async def generate_report_solution(body: dict = Body(...)):
    rounds = body.get("rounds", [])
    player_name = body.get("playerName", "친구")
    
    if not rounds:
        raise HTTPException(status_code=400, detail="No rounds provided for report solution")
        
    # Format the round history for the prompt
    history_str = ""
    for idx, r in enumerate(rounds):
        scenario = r.get("scenario", {})
        situation = scenario.get("situation", "")
        dialogue = " / ".join(scenario.get("dialogue", []))
        answer = r.get("answer", "")
        score = r.get("result", {}).get("score", 0)
        grade = r.get("result", {}).get("grade", "F")
        
        history_str += f"""
[라운드 {idx+1}]
- 상황: {situation}
- 준원이의 대사: {dialogue}
- {player_name}의 참교육 대응: "{answer}" (획득 점수: {score}점, 등급: {grade})
"""

    system_prompt = f"""너는 '준원이 족치기' 게임의 전문 참교육 마스터이자 심리 상담사 AI야.
사용자({player_name})가 5라운드 동안 준원이를 참교육하며 누적한 대화 내역과 점수를 보고, 사용자 {player_name}의 훈육 성향을 프로파일링하고 개선 솔루션을 제시해야 해.

재미있고 날카로우며 현실적인 어조로 다음 3가지 항목을 분석해줘:
1. 참교육 성향 분석 (예: 팩폭형, 감정호소형, 무력진압형 등 위트 있는 이름 부여)
2. 준원이를 대할 때 발견된 약점 및 보완점
3. 앞으로 준원이를 확실히 굴복시키고 눈물 흘리게 만들기 위한 핵심 솔루션 가이드

반드시 아래 JSON 형식으로만 응답해. JSON 외의 다른 텍스트는 절대 포함하지 마:
{{
  "style": "사용자의 참교육 성향 분석 (2-3문장)",
  "weakness": "준원이를 대할 때의 약점 (2-3문장)",
  "solution": "앞으로의 100% 참교육 솔루션 가이드 (3-4문장)"
}}"""

    user_prompt = f"""여기에 사용자 {player_name}의 5라운드 플레이 기록이 있어:
{history_str}

이 기록을 기반으로 참교육 성향 분석, 약점 분석, 최종 길들이기 솔루션을 제공해줘."""

    result_text = await call_gemini(system_prompt, user_prompt, response_mime_type="application/json")
    
    try:
        parsed = json.loads(result_text)
    except:
        import re
        json_match = re.search(r'\{[\s\S]*\}', result_text)
        if json_match:
            try:
                parsed = json.loads(json_match.group(0))
            except:
                raise HTTPException(status_code=502, detail="Failed to parse solution JSON")
        else:
            raise HTTPException(status_code=502, detail="AI did not return valid JSON")
            
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
