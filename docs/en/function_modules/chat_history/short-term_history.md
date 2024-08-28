# Short-term memory

Labridge stores a recent interaction record for each member or member group. 
This interaction record follows a queue structure with a fixed length.

Each time an interaction occurs with a member, 
the corresponding interaction record is input to the **LLM** as part of the prompt 
along with the current message from that member.

Users can manually clear the short-term memory to start a new topic, avoiding interference from previous conversations.


