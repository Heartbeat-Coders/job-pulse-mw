# # app/openai_utils.py

# import openai
# from app.config import get_settings

# # Load OpenAI API key from environment
# settings = get_settings()
# openai.api_key = settings.OPENAI_API_KEY

# def score_cv_with_openai(cv_text: str, job_description: str) -> dict:
#     """
#     Uses OpenAI to score a CV against a job description.
#     Returns a score (0–100) and a short reason.
#     """
#     prompt = f"""
# You are a recruitment assistant.

# Job Description:
# {job_description}

# Candidate CV:
# {cv_text}

# Evaluate how well the CV matches the job. Respond with:

# Score: <number from 0 to 100>
# Reason: <one-sentence explanation>
# """

#     try:
#         response = openai.ChatCompletion.create(
#             model="gpt-4",  # or use "gpt-3.5-turbo" for faster/cheaper access
#             messages=[
#                 {"role": "user", "content": prompt}
#             ],
#             temperature=0.3
#         )

#         reply = response.choices[0].message['content'].strip()
#         lines = reply.splitlines()

#         # Parse score and reason
#         score_line = next((l for l in lines if l.lower().startswith("score:")), "")
#         reason_line = next((l for l in lines if l.lower().startswith("reason:")), "")

#         score = int(score_line.split(":")[1].strip()) if score_line else None
#         reason = reason_line.split(":", 1)[1].strip() if reason_line else "No reason provided."

#         return {"score": score, "reason": reason}

#     except Exception as e:
#         return {"score": None, "reason": f"Error during AI scoring: {str(e)}"}
