# Yoga Mini Program

Native WeChat Mini Program client for member and coach workflows.

## Commands

```bash
npm install
npm run lint
npm run typecheck
npm test
```

Open this directory in WeChat DevTools. Development requests use `http://127.0.0.1:8000`; trial and release builds use `https://yoga.tuitukj.com`. Copy `project.private.config.example.json` to the ignored `project.private.config.json` for local overrides.

The development AppID is public project configuration. Backend AppSecret, identity pepper, JWTs, passwords, binding tickets, raw OpenID, and `session_key` must not be committed or logged.
