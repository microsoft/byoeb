import re
from byoeb_core.llms.base import BaseLLM

async def aget_related_questions(
    text,
    llm_client: BaseLLM,
    languages_translation_prompts: dict,
    system_prompt = None
):
    related_questions_dict = {}
    if not system_prompt:
        system_prompt = "Generate three related questions from the given text. Follow the instructions. 1. Each question MUST be **DISTINCT** i.e., intended to elicit different information. \n\n2. Each question's length MUST be **<character_limit>60</character_limit> CHARACTERS OR LESS**. \n\n3. Respond with the three questions in XML format.  \nSample output:  \n<related_questions> \n<q_1>Content of first question</q_1> \n<q_2>Content of second question</q_2> \n<q_3>Content of third question</q_3> \n</related_questions> \n\n</instructions>"

    prompt = [{"role": "system", "content": system_prompt}]
    prompt.append({"role": "user", "content": text})
    llm_response, resp = await llm_client.agenerate_response(prompt)
    related_questions = re.findall(r"<q_\d+>(.*?)</q_\d+>", resp)
    related_questions_dict["en"] = related_questions

    for lang, translation_prompt in languages_translation_prompts.items():
        user_prompt = f"""Translate the following list of questions <en_questions> {related_questions} </en_questions> from english to desired language.
        Maintain the output structure as follows:
        <related_questions>
        <q_1>Translated question 1</q_1>
        <q_2>Translated question 2</q_2>
        <q_3>Translated question 3</q_3>
        </related_questions>
        Note above is a sample for three questions follow same based on number of questions.
        """
        prompt = [{"role": "system", "content": translation_prompt}]
        prompt.append({"role": "user", "content": user_prompt})
        llm_response, resp = await llm_client.agenerate_response(prompt)
        related_questions = re.findall(r"<q_\d+>(.*?)</q_\d+>", resp)
        related_questions_dict[lang] = related_questions
    
    return related_questions_dict
        