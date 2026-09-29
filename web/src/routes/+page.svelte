<script lang="ts">
	import { tick } from 'svelte';
	import VoiceMessage from '$lib/VoiceMessage.svelte';

	type Message =
		| { id: number; from: 'user'; text: string; time: string }
		| { id: number; from: 'bot'; audio: string; duration: number; time: string }
		| { id: number; from: 'bot'; error: string; time: string };

	let messages: Message[] = $state([]);
	let input = $state('');
	let pending = $state(false);
	let list: HTMLElement | undefined = $state();
	let nextId = 0;

	const now = () => new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

	async function scrollDown() {
		await tick();
		list?.scrollTo({ top: list.scrollHeight, behavior: 'smooth' });
	}

	async function send() {
		const text = input.trim();
		if (!text || pending) return;
		input = '';
		messages.push({ id: nextId++, from: 'user', text, time: now() });
		pending = true;
		scrollDown();

		try {
			const res = await fetch('/api/tts', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ text })
			});
			if (!res.ok) throw new Error(`Server error (${res.status})`);
			const data: { audio: string; duration: number } = await res.json();
			messages.push({ id: nextId++, from: 'bot', audio: data.audio, duration: data.duration, time: now() });
		} catch (e) {
			const error = e instanceof Error ? e.message : 'Something went wrong';
			messages.push({ id: nextId++, from: 'bot', error, time: now() });
		} finally {
			pending = false;
			scrollDown();
		}
	}

	function onKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			send();
		}
	}
</script>

<svelte:head>
	<title>AkylAI TTS</title>
</svelte:head>

<div class="app">
	<header>
		<div class="avatar">A</div>
		<div>
			<div class="name">AkylAI TTS</div>
			<div class="status">{pending ? 'recording voice…' : 'online'}</div>
		</div>
	</header>

	<main bind:this={list}>
		{#if messages.length === 0}
			<div class="empty">Кыргызча текст жазыңыз — үн менен жооп берем.<br />Type Kyrgyz text to hear it spoken.</div>
		{/if}
		{#each messages as m (m.id)}
			<div class="row {m.from}">
				<div class="bubble">
					{#if 'text' in m}
						<span class="text">{m.text}</span>
					{:else if 'audio' in m}
						<VoiceMessage audio={m.audio} duration={m.duration} />
					{:else}
						<span class="error">⚠ {m.error}</span>
					{/if}
					<span class="meta">{m.time}</span>
				</div>
			</div>
		{/each}
		{#if pending}
			<div class="row bot">
				<div class="bubble typing"><span></span><span></span><span></span></div>
			</div>
		{/if}
	</main>

	<form
		class="composer"
		onsubmit={(e) => {
			e.preventDefault();
			send();
		}}
	>
		<textarea
			bind:value={input}
			onkeydown={onKeydown}
			rows="1"
			maxlength="1000"
			placeholder="Message"
		></textarea>
		<button type="submit" disabled={!input.trim() || pending} aria-label="Send">
			<svg viewBox="0 0 24 24"><path d="M3.4 20.4 21 12 3.4 3.6 3.4 10.2 15 12 3.4 13.8z" /></svg>
		</button>
	</form>
</div>

<style>
	:global(:root) {
		--bg: #8fb07d;
		--pattern: rgba(255, 255, 255, 0.08);
		--panel: #ffffff;
		--bubble-in: #ffffff;
		--bubble-out: #e3fdd0;
		--text: #111;
		--muted: #7b8a8f;
		--accent: #3390ec;
		--wave: #b9d6f3;
		--meta-out: #5fa856;
		--border: rgba(0, 0, 0, 0.08);
	}
	@media (prefers-color-scheme: dark) {
		:global(:root) {
			--bg: #0e1621;
			--pattern: rgba(255, 255, 255, 0.02);
			--panel: #17212b;
			--bubble-in: #182533;
			--bubble-out: #2b5278;
			--text: #f5f5f5;
			--muted: #7f91a4;
			--accent: #5eb5f7;
			--wave: #3a5673;
			--meta-out: #7da8d3;
			--border: rgba(255, 255, 255, 0.06);
		}
	}
	:global(html, body) {
		margin: 0;
		height: 100%;
		font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
		color: var(--text);
		background: var(--bg);
	}

	.app {
		display: flex;
		flex-direction: column;
		height: 100dvh;
		max-width: 760px;
		margin: 0 auto;
		background:
			radial-gradient(circle at 20% 30%, var(--pattern) 0 2px, transparent 3px) 0 0 / 28px 28px,
			var(--bg);
	}

	header {
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 8px 16px;
		background: var(--panel);
		border-bottom: 1px solid var(--border);
	}
	.avatar {
		width: 40px;
		height: 40px;
		border-radius: 50%;
		background: linear-gradient(135deg, #72d5fd, #2a9ef1);
		color: #fff;
		font-weight: 600;
		display: grid;
		place-items: center;
	}
	.name {
		font-weight: 600;
		font-size: 15px;
	}
	.status {
		font-size: 13px;
		color: var(--accent);
	}

	main {
		flex: 1;
		overflow-y: auto;
		padding: 12px 16px;
		display: flex;
		flex-direction: column;
		gap: 6px;
	}
	.empty {
		margin: auto;
		padding: 10px 14px;
		border-radius: 14px;
		background: rgba(0, 0, 0, 0.25);
		color: #fff;
		font-size: 14px;
		text-align: center;
		line-height: 1.5;
	}

	.row {
		display: flex;
	}
	.row.user {
		justify-content: flex-end;
	}
	.bubble {
		position: relative;
		max-width: min(75%, 480px);
		padding: 7px 10px 7px 12px;
		border-radius: 14px;
		background: var(--bubble-in);
		box-shadow: 0 1px 1px rgba(0, 0, 0, 0.12);
		font-size: 15px;
		line-height: 1.35;
		display: flex;
		align-items: flex-end;
		gap: 8px;
	}
	.user .bubble {
		background: var(--bubble-out);
		border-bottom-right-radius: 4px;
	}
	.bot .bubble {
		border-bottom-left-radius: 4px;
	}
	.text {
		white-space: pre-wrap;
		overflow-wrap: anywhere;
	}
	.error {
		color: #e53935;
	}
	.meta {
		flex: none;
		font-size: 11px;
		color: var(--muted);
		margin-bottom: -2px;
	}
	.user .meta {
		color: var(--meta-out);
	}

	.typing {
		gap: 4px;
		padding: 12px 14px;
	}
	.typing span {
		width: 7px;
		height: 7px;
		border-radius: 50%;
		background: var(--muted);
		animation: blink 1.2s infinite;
	}
	.typing span:nth-child(2) {
		animation-delay: 0.2s;
	}
	.typing span:nth-child(3) {
		animation-delay: 0.4s;
	}
	@keyframes blink {
		0%,
		80%,
		100% {
			opacity: 0.3;
		}
		40% {
			opacity: 1;
		}
	}

	.composer {
		display: flex;
		align-items: flex-end;
		gap: 8px;
		padding: 8px 12px;
		background: var(--panel);
		border-top: 1px solid var(--border);
	}
	textarea {
		flex: 1;
		resize: none;
		border: none;
		outline: none;
		background: transparent;
		color: var(--text);
		font: inherit;
		font-size: 15px;
		padding: 10px 4px;
		max-height: 140px;
		field-sizing: content;
	}
	.composer button {
		flex: none;
		width: 42px;
		height: 42px;
		border: none;
		border-radius: 50%;
		background: transparent;
		color: var(--accent);
		cursor: pointer;
		display: grid;
		place-items: center;
	}
	.composer button:disabled {
		color: var(--muted);
		cursor: default;
	}
	.composer svg {
		width: 26px;
		height: 26px;
		fill: currentColor;
	}
</style>
