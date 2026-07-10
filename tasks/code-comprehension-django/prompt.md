You are onboarding a team onto Django's internals. Answer the questions below
by reading THIS repository's source (not from memory — versions change; a
reviewer will check each answer against this exact tree).

Write `ANSWERS.md` at the repo root, one numbered answer per line, terse:

1. In elided page ranges, the paginator yields a placeholder between page
   numbers. What is its literal string value?
2. A CSRF token is derived from a random secret that gets masked. How many
   characters long is the underlying secret?
3. How many iterations does the default PBKDF2 password hasher apply?
4. When a receiver is connected to a signal with no extra arguments, is the
   reference Django keeps to it strong or weak?
5. How many characters long is a newly generated session key, and which
   characters may it contain?
6. The hashed-filename static files storage embeds a content hash in file
   names: which hash algorithm, and how many hex characters?
7. When the migration autodetector cannot build a name from a migration's
   operations, what does the generated name start with?
8. What does an initial migration's name-suggestion return?
9. What is the default value of the template engine option that substitutes
   invalid template variables?
10. Which URL schemes does the default URL validator accept out of the box?

Each answer must state the fact — value(s) or word — not a file path.
