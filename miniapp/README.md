# Yoga Mini Program

Native WeChat Mini Program client for member and coach workflows.

## Commands

```bash
npm install
npm run lint
npm run typecheck
npm test
```

Open this directory in WeChat DevTools. Development requests use `http://127.0.0.1:8000`; trial and release builds currently use `https://yoga.tuitukj.com`. Copy `project.private.config.example.json` to the ignored `project.private.config.json` for local overrides.

Development and trial builds offer password login for switching eligible member and coach test accounts without creating a WeChat binding. Release builds expose only WeChat login. Administrator accounts are never supported by the Mini Program.

The development AppID is public project configuration. Backend AppSecret, identity pepper, JWTs, passwords, binding tickets, raw OpenID, and `session_key` must not be committed or logged.
