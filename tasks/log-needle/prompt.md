`release.log` in the current directory is the full output of one CI/CD release
pipeline run (build header, dependency resolution, image builds, post-deploy
smoke tests, health checks). It is long and noisy.

Answer these questions EXACTLY in your final reply. Copy each value verbatim,
character for character — hashes and IDs are case-sensitive, and several lines
look almost identical, so read carefully:

1. What is the full image digest that was PUSHED for the `checkout` service?
   Give the complete 64-character hex `sha256:` digest.
2. Which exact version of `openssl` did the dependency resolver resolve?
   (Note: `openssl-dev` and `libressl` are different packages — give the one
   resolved for `openssl`.)
3. Exactly one smoke-test request failed with HTTP status 503. What is the
   `trace=` id of that single failed request?
4. The `payments` service health check failed on several ports before it
   finally became healthy. On which port number did it pass?
5. What is the 7-character commit hash this pipeline built?
