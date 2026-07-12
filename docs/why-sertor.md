# What Sertor is, and why it matters

*A plain-language overview — no jargon, no code. If you just want to get it running, jump to the
[getting-started guide](getting-started.md).*

## The problem

Every software project is a pile of two things: **code** (the parts that *do* the work) and
**documentation** (the parts that *explain* it) — often thousands of files. When someone asks a
question — *"where is login handled?"*, *"why does this behave that way?"* — the answer is in there
somewhere, but **finding it is the hard part**. You have to know where to look, and read by hand.

This is doubly true for an **AI assistant**. Ask one about your project and, without help, it answers
*from memory* — from the generic patterns it learned, not from *your* code. Sometimes it's right.
Sometimes it confidently makes things up.

## What Sertor is

**Sertor is a librarian for your project.** It reads everything ahead of time, organizes it, and when a
question comes in it hands over *the right pages* — and tells you where they came from. It doesn't answer
the question itself (that's the AI assistant's job); Sertor is the part that **finds and hands over the
relevant material**, fast, with the source attached.

The result: your assistant stops guessing and starts answering **anchored to what your project actually
says** — able to point at the exact file and paragraph.

## Why Sertor is different: code and docs, together

Most tools make the assistant read **either** the code **or** the docs. Sertor's whole idea is to hand
over **both at once**, for the same question:

> **The code says *what it does*. The documentation says *why*.**

Neither half is the whole answer. The code shows the rule; the docs explain the reason behind it. Fused
together, they're understanding.

Here's what that looks like in practice. Ask *"how does authentication work?"* and Sertor hands your
assistant two things side by side:

- **the why** — the design note or spec: *"sessions are signed, tokens rotate every 24 hours, here's the
  reasoning"*
- **the what** — the actual code: *"`verify_session()` checks the signature and expiry"*

The assistant now has **the rule and the reason** in a single lookup. The code alone wouldn't have
explained *why*; the docs alone wouldn't have shown *how*. That fusion is the point — and it's the one
thing Sertor is built to do better than anything else.

## Why it works on any project

Sertor makes no assumptions about *what* your project is. It attaches to it only as a reader, so it fits:

- a **code + docs** project (an app with its documentation),
- a **docs-only** project (a knowledge base, a wiki, a folder of PDFs),
- a **code-only** project (a library with no written docs).

And it's **portable and lock-in-free**: it runs on your own machine if you want, and it isn't tied to
any one AI provider or storage vendor. You can move it from one project to the next.

## How you'd actually use it

You install Sertor into a project, point it at the folder, and let it read (index) everything once. From
then on, your AI assistant — Claude Code or GitHub Copilot — can search the project by meaning and get
back code and docs together, with sources. As the project grows, Sertor keeps a **living notebook** (an
"LLM Wiki") that gets richer every session instead of being rebuilt from scratch each time.

## The honest part

We build Sertor by **using it on itself** every day (we call it *dogfooding*): it keeps its own notebook
and answers our own questions with its own tools. It's the fastest way to notice when something is
broken — we feel it first.

---

**Want to try it?** The single path from nothing to your first result is the
**[getting-started guide](getting-started.md)**. For the one-screen pitch, see the
[README](../README.md); to learn *how to search well* once it's running, see
[searching a project](retrieval.md).
