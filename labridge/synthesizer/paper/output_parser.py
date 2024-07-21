import re


rr = """
	References start
**Reference paper 1**
	**Title**: Proximal Policy Optimization Algorithms
	**Possessor**: 张三
>References end

References start
**Reference paper 2**
	**Title**: Soft Actor-Critic Algorithms and Applications
	**Possessor**: 张三
>References end

Answer: The Proximal Policy Optimization (PPO) and Soft Actor-Critic (SAC) algorithms are both designed to address challenges in reinforcement learning, specifically focusing on improving the efficiency and stability of learning processes. However, there are key differences between the two:

1. **Objective Function**: PPO uses a clipped surrogate objective function, which aims to limit the impact of large policy updates to ensure stability. SAC, on the other hand, employs a soft Q-learning approach where the Q-values are modeled as a Gaussian distribution, allowing for a more flexible exploration strategy.

2. **Stability and Efficiency**: PPO is designed to be more stable and efficient in terms of sample complexity compared to other policy gradient methods. Its clipping mechanism helps in achieving a balance between exploration and exploitation, making it less sensitive to hyperparameter tuning. SAC, while also aiming for stability, uses entropy regularization to encourage exploration, which can lead to more diverse behavior in the early stages of training.

3. **Implementation Complexity**: PPO is generally considered easier to implement than SAC due to its straightforward formulation and fewer hyperparameters to tune. SAC, with its use of entropy regularization and reparameterization trick for efficient gradient computation, might require more sophisticated setup and understanding of its underlying principles.

4. **Convergence**: PPO tends to converge faster and more reliably than SAC, especially in high-dimensional action spaces. SAC, while capable of handling complex tasks, might require careful tuning of its temperature parameter to balance exploration and exploitation effectively.

5. **Exploration Strategy**: SAC employs a natural policy gradient approach combined with entropy regularization to naturally encourage exploration. PPO, through its surrogate objective, indirectly promotes exploration by maintaining a balance between the current policy and the target policy, without explicitly adding an exploration bonus.

In summary, while both algorithms aim to improve upon traditional policy gradient methods, PPO focuses on stability and efficiency through a clipped surrogate objective, whereas SAC emphasizes exploration through entropy regularization. The choice between the two would depend on the specific requirements of the task, such as the need for stability, efficiency, or exploration capabilities.
	"""

def paper_query_output_parser(response: str, answer_len_threshold: int = 3):
	ref_start = "References start"
	ref_end = "References end"
	ans_start = "Answer: "
	title_name = "Title"
	possessor_name = "Possessor"

	chunks = re.split(f"{ref_end}|{ans_start}", response)
	answer = chunks[-1]
	if len(answer) < answer_len_threshold:
		return response

	while (not answer[0].isalnum()) and len(answer) > 1:
		answer = answer[1:]

	refs = "\n".join(chunks[:-1])
	refs = "\n".join(refs.split(ref_start))

	refs_list = []
	ref_chunks = refs.split('**')
	for idx, item in enumerate(ref_chunks):
		if item == title_name:
			title = re.sub(r'\W', '', ref_chunks[idx + 1])
			refs_list.append([title, ])
		elif item == possessor_name:
			possessor = re.sub(r'\W', '', ref_chunks[idx + 1])
			refs_list[-1].append(possessor)

	ref_str = "References: \n"
	for ref_idx in range(len(refs_list)):
		ref_str += f"- Ref{ref_idx + 1}: {refs_list[ref_idx][0]}\n"
		ref_str += f"\t- 这篇文章 **{refs_list[ref_idx][1]}** 比较熟悉，或许你可以请教一下他（她）。\n"

	output = f"{answer}\n\n{ref_str}"
	return output
