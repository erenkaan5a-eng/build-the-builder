Build the Builder kickoff - October 10

[VIEW RECORDING - 50 mins (No highlights)](https://fathom.video/share/SCFTpw9gPFqxxEqk49PbM3HFjSros35m)

Meeting Purpose
[Kickoff for the "Build the Builder" hackathon.](https://fathom.video/share/SCFTpw9gPFqxxEqk49PbM3HFjSros35m?tab=summary&timestamp=863.0)
Key Takeaways
- [The Challenge: Automate agent creation. Your "builder agent" must generate a debt collection "phone agent" from unstructured specs (e.g., meeting notes) by outputting a ~600-line JSON workflow.](https://fathom.video/share/SCFTpw9gPFqxxEqk49PbM3HFjSros35m?tab=summary&timestamp=947.0)
- [The Goal: Replicate Freya's success. Freya's agents recently beat human collectors (53% vs. 51% collection rate) by iterating on call data. Your builder must automate this process.](https://fathom.video/share/SCFTpw9gPFqxxEqk49PbM3HFjSros35m?tab=summary&timestamp=225.0)
- [The Prize: A Y Combinator (YC) interview. The winning builder will be evaluated on its ability to handle unseen scenarios, measured by agent quality and build speed.](https://fathom.video/share/SCFTpw9gPFqxxEqk49PbM3HFjSros35m?tab=summary&timestamp=863.0)
- [The Strategy: First, manually build a phone agent to learn the platform. Then, write a builder agent that can automate the process for new, unseen specs.](https://fathom.video/share/SCFTpw9gPFqxxEqk49PbM3HFjSros35m?tab=summary&timestamp=1440.0)
Topics
Freya's Vision & Success
- [Origin: Spun out of Caltech/UPenn research on hallucination-resistant LLMs.](https://fathom.video/share/SCFTpw9gPFqxxEqk49PbM3HFjSros35m?tab=summary&timestamp=39.0)
- [Focus: AI call centers for regulated industries (banking, insurance) where accuracy is critical.](https://fathom.video/share/SCFTpw9gPFqxxEqk49PbM3HFjSros35m?tab=summary&timestamp=99.0)
- [Key Achievement: An AI agent beat a human collector (53% vs. 51% collection rate), a world-first.](https://fathom.video/share/SCFTpw9gPFqxxEqk49PbM3HFjSros35m?tab=summary&timestamp=225.0)
- [Platform Advantage: A feedback loop that analyzes call data, finds root causes (LLM, STT, VAD errors), and proposes fixes, enabling rapid agent iteration.](https://fathom.video/share/SCFTpw9gPFqxxEqk49PbM3HFjSros35m?tab=summary&timestamp=672.0)
The "Build the Builder" Hackathon
- [Core Task: Build a "builder agent" that automatically creates a "phone agent" from customer specs.](https://fathom.video/share/SCFTpw9gPFqxxEqk49PbM3HFjSros35m?tab=summary&timestamp=846.0)
- [Phone Agent: A debt collection agent built on the Freya platform.](https://fathom.video/share/SCFTpw9gPFqxxEqk49PbM3HFjSros35m?tab=summary&timestamp=488.0)
  - [Must handle identity verification (a legal requirement) and debt collection logic.](https://fathom.video/share/SCFTpw9gPFqxxEqk49PbM3HFjSros35m?tab=summary&timestamp=1020.0)
  - [Interacts with a provided mock banking API.](https://fathom.video/share/SCFTpw9gPFqxxEqk49PbM3HFjSros35m?tab=summary&timestamp=1154.0)
- [Builder Agent: Your creation, built using any tools (e.g., Codex, Claude).](https://fathom.video/share/SCFTpw9gPFqxxEqk49PbM3HFjSros35m?tab=summary&timestamp=1320.0)
  - [Input: Unstructured customer specs (e.g., meeting notes).](https://fathom.video/share/SCFTpw9gPFqxxEqk49PbM3HFjSros35m?tab=summary&timestamp=947.0)
  - [Output: A ~600-line JSON workflow file that defines the phone agent on the Freya platform.](https://fathom.video/share/SCFTpw9gPFqxxEqk49PbM3HFjSros35m?tab=summary&timestamp=1223.0)
- [Evaluation:](https://fathom.video/share/SCFTpw9gPFqxxEqk49PbM3HFjSros35m?tab=summary&timestamp=1237.0)
  - [Benchmark: The phone agent's performance against simulated customer personas (angry, scammer, etc.).](https://fathom.video/share/SCFTpw9gPFqxxEqk49PbM3HFjSros35m?tab=summary&timestamp=1237.0)
  - [Metrics: Agent quality, adherence to rules (e.g., max 2 payment requests), and build speed.](https://fathom.video/share/SCFTpw9gPFqxxEqk49PbM3HFjSros35m?tab=summary&timestamp=1623.0)
  - [Deliverable: The final JSON workflow file.](https://fathom.video/share/SCFTpw9gPFqxxEqk49PbM3HFjSros35m?tab=summary&timestamp=2298.0)
Hackathon Timeline & Rules
- [Phase 1 (Now → Sat, 5 PM): Learn the platform by manually building a phone agent. Use this knowledge to write your builder agent.](https://fathom.video/share/SCFTpw9gPFqxxEqk49PbM3HFjSros35m?tab=summary&timestamp=1440.0)
- [Phase 2 (Sat, 5 PM → 8 PM): A 3-hour live challenge.](https://fathom.video/share/SCFTpw9gPFqxxEqk49PbM3HFjSros35m?tab=summary&timestamp=1787.0)
  - [New, unseen customer specs will be released.](https://fathom.video/share/SCFTpw9gPFqxxEqk49PbM3HFjSros35m?tab=summary&timestamp=1348.0)
  - [Your builder agent must generate a new phone agent from scratch.](https://fathom.video/share/SCFTpw9gPFqxxEqk49PbM3HFjSros35m?tab=summary&timestamp=1348.0)
  - [Platform testing will be limited; local simulation is encouraged.](https://fathom.video/share/SCFTpw9gPFqxxEqk49PbM3HFjSros35m?tab=summary&timestamp=2174.0)
- [Phase 3 (Sat, 8 PM → 11 PM): Freya conducts final evaluations.](https://fathom.video/share/SCFTpw9gPFqxxEqk49PbM3HFjSros35m?tab=summary&timestamp=1787.0)
- [Resources:](https://fathom.video/share/SCFTpw9gPFqxxEqk49PbM3HFjSros35m?tab=summary&timestamp=1281.0)
  - [Starter Kit: Includes a default workflow, mock banking API, and practice customers.](https://fathom.video/share/SCFTpw9gPFqxxEqk49PbM3HFjSros35m?tab=summary&timestamp=1281.0)
  - [Budget: The initial $10 credit will be increased.](https://fathom.video/share/SCFTpw9gPFqxxEqk49PbM3HFjSros35m?tab=summary&timestamp=2048.0)
  - [Support: Email ](https://fathom.video/share/SCFTpw9gPFqxxEqk49PbM3HFjSros35m?tab=summary&timestamp=1574.0)yavuz@freya.voice[ for help.](https://fathom.video/share/SCFTpw9gPFqxxEqk49PbM3HFjSros35m?tab=summary&timestamp=1574.0)
Next Steps
- [Freya:](https://fathom.video/share/SCFTpw9gPFqxxEqk49PbM3HFjSros35m?tab=summary&timestamp=2466.0)
  - [Email hackathon details, starter kits, and the meeting recording.](https://fathom.video/share/SCFTpw9gPFqxxEqk49PbM3HFjSros35m?tab=summary&timestamp=2400.0)
  - [Increase participant platform budgets.](https://fathom.video/share/SCFTpw9gPFqxxEqk49PbM3HFjSros35m?tab=summary&timestamp=2048.0)
- [Participants:](https://fathom.video/share/SCFTpw9gPFqxxEqk49PbM3HFjSros35m?tab=summary&timestamp=1417.0)
  - [Check email for hackathon materials.](https://fathom.video/share/SCFTpw9gPFqxxEqk49PbM3HFjSros35m?tab=summary&timestamp=1945.0)
  - [Begin by manually building a phone agent to learn the platform.](https://fathom.video/share/SCFTpw9gPFqxxEqk49PbM3HFjSros35m?tab=summary&timestamp=1440.0)
  - [Design a builder agent capable of generating agents from new specs.](https://fathom.video/share/SCFTpw9gPFqxxEqk49PbM3HFjSros35m?tab=summary&timestamp=1348.0)