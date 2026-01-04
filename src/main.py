import asyncio
import json
import os

from dotenv import load_dotenv  # 추가

# .env 파일 로드 (환경 변수로 등록됨)
load_dotenv()

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from google.adk.agents import SequentialAgent, LlmAgent

from data import question

generator = LlmAgent(
    name="GenerateData",
    model="gemini-2.5-flash",
    instruction="generate JSON-LD from user input.",
    output_key="result",
)
validator = LlmAgent(
    name="ValidateInput",
    model="gemini-2.5-flash",
    instruction="Validate the {result} is valid JSON-LD",
    output_key="validation_status",
)
reporter = LlmAgent(
    name="ReportResult",
    model="gemini-2.5-flash",
    instruction="Report the result from {result} only if {validation_status} is valid.",
)


root_agent = SequentialAgent(
    name="DataPipeline", sub_agents=[generator, validator, reporter]
)


async def main():
    # 1. 질문하고 결과 받기
    result = await ask(question=question)
    print(result)  # 콘솔 확인용

    # 2. 저장할 폴더 경로 정의 (output)
    output_dir = "output"
    
    # 폴더가 없으면 생성 (exist_ok=True: 이미 있어도 에러 안 남)
    os.makedirs(output_dir, exist_ok=True)

    # 3. 파일 경로 정의 (output/result.json)
    file_path = os.path.join(output_dir, "result.json")

    # 4. JSON 파일로 저장
    with open(file_path, "w", encoding="utf-8") as f:
        # 만약 result가 단순 문자열이라면 딕셔너리로 감싸는 것이 일반적인 JSON 형태입니다.
        # 예: result가 "안녕하세요"라면 -> {"content": "안녕하세요"} 로 저장
        data_to_save = result
        if not isinstance(result, (dict, list)):
             data_to_save = {"content": result}

        json.dump(data_to_save, f, ensure_ascii=False, indent=2)

    print(f"★ 결과가 '{file_path}'에 저장되었습니다.")



async def ask(question: str):
    session_service = InMemorySessionService()
    
    await session_service.create_session(app_name="DataPipelineApp", session_id="session1", user_id="user1")

  
    # 1. Runner 초기화 (세션 관리 및 실행 담당)
    runner = Runner(
        agent=root_agent,
        session_service=session_service,  # 메모리 내에서 세션 상태 유지
        app_name="DataPipelineApp",
    )

    # 2. 실행 및 이벤트 루프 (비동기 실행 권장)
    # 초기 입력 메시지 설정
    user_input = types.Content(
        role="user",
        parts=[
            types.Part.from_text(text=question)
        ],
    )

    print("--- Pipeline Started ---")

    # runner.run_async()는 제너레이터로서 Event 객체를 하나씩 반환합니다.
    async for event in runner.run_async(
        user_id="user1", session_id="session1", new_message=user_input
    ):

        # [접근 방법 1] 어떤 Agent가 보낸 이벤트인지 확인 (event.author)
        # 예: 'ValidateInput', 'ProcessData', 'ReportResult' 등
        agent_name = event.author
            
        # [접근 방법 3] 특정 Agent의 최종 결과만 필요할 때
        # 예: 마지막 'ReportResult' 에이전트의 결과만 찾기
        if agent_name == "ReportResult" and event.is_final_response():
            return event.content.parts[0].text

def save_result(data: str, folder: str = "output", filename: str = "result.json"):
    """
    데이터를 지정된 폴더의 JSON 파일로 저장합니다.
    """
    # 1. 폴더 생성
    os.makedirs(folder, exist_ok=True)
    
    # 2. 파일 경로 설정
    file_path = os.path.join(folder, filename)

    # 3. JSON 구조로 변환 (문자열이 들어오면 객체로 감쌈)
    json_data = data
    if not isinstance(data, (dict, list)):
        json_data = {"question_result": data}

    # 4. 저장
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n★ 저장 완료: {file_path}")
    
    
    
async def main():
    result_text = await ask(question=question)

    if result_text:
        save_result(result_text)
    else:
        print("\n[!] 유효한 답변을 얻지 못했습니다.")              
    

if __name__ == "__main__":
    asyncio.run(main())

