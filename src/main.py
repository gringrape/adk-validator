import asyncio

from dotenv import load_dotenv  # 추가

# .env 파일 로드 (환경 변수로 등록됨)
load_dotenv()

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from google.adk.agents import SequentialAgent, LlmAgent

validator = LlmAgent(
    name="ValidateInput",
    model="gemini-2.5-flash",
    instruction="Validate the input is question about science(must)",
    output_key="validation_status",
)
processor = LlmAgent(
    name="ProcessData",
    model="gemini-2.5-flash",
    instruction="Process data if {validation_status} is 'valid'.",
    output_key="result",
)
reporter = LlmAgent(
    name="ReportResult",
    model="gemini-2.5-flash",
    instruction="Report the result from {result}.",
)


root_agent = SequentialAgent(
    name="DataPipeline", sub_agents=[validator, processor, reporter]
)


async def main():
  result = await ask(question="What is the impact of CO2 on global warming?")
  print(result)



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
              
    

if __name__ == "__main__":
    asyncio.run(main())
