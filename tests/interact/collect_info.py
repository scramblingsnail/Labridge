import json
import copy

from llama_index.core.settings import Settings

from labridge.llm.models import get_models
from labridge.interact.collect.pipeline import collect_info_from_user, acollect_info_from_user
from labridge.interact.collect.types.common_info import CollectingCommonInfo
from labridge.interact.collect.types.select_info import CollectingSelectInfo


if __name__ == "__main__":
	import asyncio

	llm, embed_model = get_models()
	Settings.llm = llm
	Settings.embed_model = embed_model

	required_infos = {"college": "", "research field": "", "age": "", }
	query_str = "请问您毕业于哪所大学，目前感兴趣的研究领域是什么？"

	info_list = []
	for key in required_infos.keys():
		common_infos = CollectingCommonInfo(
			info_name=key,
			info_description=required_infos[key],
		)
		info_list.append(common_infos)

	choices = {
		"强化学习优化忆阻器写入": "利用强化学习方法，获得写入成本优于传统反馈式写入方法的写入策略",
		"面向存算一体硬件的深度学习编译": "开发面向存算一体硬件的深度学习编译器",
		"实验室智能助手": "利用大语言模型构建实验室的智能助手，提高同学们的科研效率",
	}

	select_info = CollectingSelectInfo(
		info_name="current_experiment",
		info_description="用户正在进行中的实验",
		choices=choices,
	)

	choices_1 = {
		"存算一体工程师": "这个职业负责开发存算一体硬件",
		"AI推理工程师": "这个职业负责AI模型的推理优化",
		"高校教师": "这个职业负责科研、教学",
	}

	select_info1 = CollectingSelectInfo(
		info_name="target_work",
		info_description="用户理想的职业",
		choices=choices_1,
	)

	info_list.append(select_info)
	info_list.append(select_info1)

	async def async_collect():
		output_info = await acollect_info_from_user(
			user_id="杨再正",
			required_infos=info_list,
			query_str=query_str
		)
		print(output_info)

	asyncio.run(async_collect())



