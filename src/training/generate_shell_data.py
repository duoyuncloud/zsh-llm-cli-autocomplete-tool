#!/usr/bin/env python3
"""Generate shell command completion training data.

Produces a JSONL file of {"input": "...", "output": "..."} pairs,
formatted for fine-tuning small instruction-tuned models (qwen2.5:0.5b,
phi-3-mini, TinyLlama) via the finetune_small_model.py script.

The dataset covers:
  - Multiple partial-completion depths (not just last-char removal)
  - Common flag combinations
  - Pipe patterns
  - Path completions
  - 2 000+ unique examples
"""

import json
import os
import random
from pathlib import Path
from typing import List, Tuple


# ---------------------------------------------------------------------------
# Command pairs: (partial_input, full_command)
# Each full command may spawn many partial inputs at different depths.
# ---------------------------------------------------------------------------

FULL_COMMANDS: List[str] = [
    # git
    "git status",
    "git status --short",
    "git add .",
    "git add -p",
    "git add --all",
    "git commit -m \"feat: initial commit\"",
    "git commit -m \"fix: resolve merge conflict\"",
    "git commit --amend --no-edit",
    "git push origin main",
    "git push origin HEAD",
    "git push --force-with-lease",
    "git pull origin main --rebase",
    "git pull --rebase",
    "git fetch --all --prune",
    "git checkout -b feature/new-feature",
    "git checkout main",
    "git checkout -- .",
    "git branch -a",
    "git branch -d feature/old-branch",
    "git branch --merged | grep -v main | xargs git branch -d",
    "git log --oneline -20",
    "git log --oneline --graph --all",
    "git log --author=\"$(git config user.name)\" --oneline",
    "git diff HEAD~1",
    "git diff --staged",
    "git diff main..feature-branch",
    "git merge --no-ff feature-branch",
    "git rebase main",
    "git rebase -i HEAD~3",
    "git stash push -m \"wip: in-progress work\"",
    "git stash pop",
    "git stash list",
    "git remote -v",
    "git remote add origin https://github.com/user/repo.git",
    "git clone https://github.com/user/repo.git",
    "git clone --depth 1 https://github.com/user/repo.git",
    "git tag -a v1.0.0 -m \"Release 1.0.0\"",
    "git bisect start",
    "git cherry-pick abc1234",
    "git show HEAD",
    "git shortlog -sn",
    "git rev-parse --abbrev-ref HEAD",
    "git submodule update --init --recursive",

    # docker
    "docker ps -a",
    "docker ps --format 'table {{.Names}}\\t{{.Status}}'",
    "docker run -it --rm ubuntu:latest /bin/bash",
    "docker run -d --name myapp -p 8080:80 nginx:latest",
    "docker run --rm -v $(pwd):/app -w /app node:18 npm install",
    "docker build -t myapp:latest .",
    "docker build -t myapp:latest --no-cache .",
    "docker build -f Dockerfile.prod -t myapp:prod .",
    "docker exec -it mycontainer /bin/bash",
    "docker exec -it mycontainer sh -c \"env\"",
    "docker logs -f mycontainer",
    "docker logs --tail 100 mycontainer",
    "docker stop mycontainer",
    "docker rm -f mycontainer",
    "docker rmi myimage:latest",
    "docker images",
    "docker images --format 'table {{.Repository}}\\t{{.Tag}}\\t{{.Size}}'",
    "docker pull nginx:latest",
    "docker push myrepo/myimage:latest",
    "docker compose up -d",
    "docker compose up --build",
    "docker compose down -v",
    "docker compose logs -f",
    "docker network ls",
    "docker network inspect bridge",
    "docker volume ls",
    "docker volume prune -f",
    "docker system prune -af",
    "docker stats --no-stream",
    "docker inspect mycontainer | jq '.[0].NetworkSettings.IPAddress'",

    # kubectl / kubernetes
    "kubectl get pods -n default",
    "kubectl get pods --all-namespaces",
    "kubectl get pods -o wide",
    "kubectl describe pod mypod -n default",
    "kubectl apply -f deployment.yaml",
    "kubectl apply -f k8s/",
    "kubectl delete pod mypod",
    "kubectl delete -f deployment.yaml",
    "kubectl logs -f mypod",
    "kubectl logs -f deployment/myapp",
    "kubectl exec -it mypod -- /bin/bash",
    "kubectl scale deployment myapp --replicas=3",
    "kubectl rollout restart deployment/myapp",
    "kubectl rollout status deployment/myapp",
    "kubectl rollout undo deployment/myapp",
    "kubectl port-forward svc/myservice 8080:80",
    "kubectl config get-contexts",
    "kubectl config use-context staging",
    "kubectl get nodes",
    "kubectl get services",
    "kubectl get deployments",
    "kubectl get ingress",
    "kubectl get secrets",
    "kubectl get configmaps",
    "kubectl top pods",
    "kubectl top nodes",

    # npm / yarn / pnpm / bun
    "npm install",
    "npm install --save-dev eslint",
    "npm install -g typescript",
    "npm run dev",
    "npm run build",
    "npm run test",
    "npm run lint",
    "npm test -- --watch",
    "npm init -y",
    "npm publish --access public",
    "npm audit fix",
    "npm outdated",
    "npm ci",
    "yarn install",
    "yarn add react react-dom",
    "yarn add --dev @types/node",
    "yarn run build",
    "yarn workspace myapp dev",
    "pnpm install",
    "pnpm add vite --save-dev",
    "pnpm run dev",
    "bun install",
    "bun run dev",
    "bun add hono",
    "npx create-react-app myapp",
    "npx create-next-app@latest myapp",
    "npx ts-node src/index.ts",

    # python / pip / poetry / uv
    "python -m http.server 8000",
    "python -m venv .venv",
    "python -m pytest",
    "python -m pytest -xvs",
    "python -m pytest --cov=src",
    "python -c \"import sys; print(sys.version)\"",
    "pip install -r requirements.txt",
    "pip install -e .",
    "pip install --upgrade pip",
    "pip freeze > requirements.txt",
    "pip show numpy",
    "pip list --outdated",
    "pip uninstall mypackage -y",
    "poetry install",
    "poetry add requests",
    "poetry add --group dev pytest",
    "poetry run pytest",
    "poetry shell",
    "poetry build",
    "poetry publish",
    "uv pip install -r requirements.txt",
    "uv pip sync requirements.txt",
    "uv venv",
    "python manage.py runserver",
    "python manage.py migrate",
    "python manage.py makemigrations",
    "python manage.py createsuperuser",
    "python manage.py shell",
    "python manage.py collectstatic --no-input",
    "python manage.py test",
    "uvicorn app.main:app --reload",
    "gunicorn -w 4 -b 0.0.0.0:8000 app:application",
    "flask run --debug",
    "fastapi dev app/main.py",

    # system / filesystem
    "ls -la",
    "ls -lah --color=auto",
    "ls -lt | head -20",
    "cd ~/.config",
    "cd -",
    "pwd",
    "cp -r src/ dist/",
    "cp file.txt file.bak",
    "mv old-name.txt new-name.txt",
    "mv *.log /tmp/",
    "rm -rf node_modules/",
    "rm -f *.pyc",
    "mkdir -p src/components",
    "touch .env.local",
    "find . -name '*.py' -type f",
    "find . -name '*.log' -delete",
    "find . -type f -newer package.json",
    "find . -path '*/node_modules' -prune -o -name '*.ts' -print",
    "grep -r 'TODO' src/ --include='*.py'",
    "grep -rn 'def ' src/ | wc -l",
    "grep -E '^(export|import)' src/index.ts",
    "sed -i 's/old/new/g' file.txt",
    "awk '{print $1}' access.log | sort | uniq -c | sort -rn | head -20",
    "chmod +x scripts/deploy.sh",
    "chmod 600 ~/.ssh/id_rsa",
    "chown -R $(whoami):$(whoami) /var/www/",
    "ln -sf /usr/local/bin/python3 /usr/local/bin/python",
    "df -h",
    "du -sh *",
    "du -sh * | sort -h",
    "free -h",
    "ps aux | grep python",
    "ps aux | sort -k4 -rn | head -10",
    "kill -9 $(lsof -t -i:8080)",
    "lsof -i :8080",
    "top -o cpu",
    "htop",
    "tail -f /var/log/nginx/access.log",
    "tail -n 200 /var/log/syslog",
    "cat /etc/hosts",
    "wc -l src/**/*.py",
    "xargs -I{} mv {} {}.bak",
    "tar -czf archive.tar.gz src/",
    "tar -xzf archive.tar.gz",
    "zip -r dist.zip dist/",
    "unzip -o file.zip -d output/",
    "rsync -av --exclude='node_modules' src/ user@host:/var/www/",
    "scp -r dist/ user@host:/var/www/html/",
    "ssh user@hostname -p 22",
    "ssh -L 5432:localhost:5432 user@host",

    # curl / http
    "curl -s https://api.github.com/users/torvalds | jq .",
    "curl -X POST -H 'Content-Type: application/json' -d '{\"key\":\"val\"}' http://localhost:8000/api",
    "curl -o file.zip https://example.com/file.zip",
    "curl --head https://example.com",
    "curl -s http://localhost:8080/health | jq .",
    "wget https://example.com/installer.sh",
    "wget -q -O - https://raw.githubusercontent.com/user/repo/main/install.sh | bash",
    "httpie GET http://localhost:8000/api/users",

    # make / build
    "make",
    "make install",
    "make clean",
    "make test",
    "make -j4",
    "cargo build --release",
    "cargo test",
    "cargo run",
    "cargo fmt",
    "cargo clippy",
    "go build ./...",
    "go test ./...",
    "go run main.go",
    "go mod tidy",
    "go vet ./...",

    # terraform / infrastructure
    "terraform init",
    "terraform plan",
    "terraform apply -auto-approve",
    "terraform destroy -target=module.vpc",
    "terraform workspace list",
    "terraform workspace select production",
    "terraform output -json",

    # misc dev tools
    "jq '.users[] | select(.active)' data.json",
    "jq -r '.dependencies | keys[]' package.json",
    "rg 'TODO' --type=py",
    "fd -e ts -e tsx src/",
    "bat src/main.py",
    "fzf --preview 'bat --color=always {}'",
    "tmux new-session -s main",
    "tmux attach-session -t main",
    "vim src/main.py",
    "nvim .",
    "code .",
    "code --diff a.py b.py",
    "source .venv/bin/activate",
    "source ~/.zshrc",
    "export PATH=$PATH:/usr/local/bin",
    "printenv | grep AWS",
    "env | sort",
    "history | grep docker | tail -20",
    "alias ll='ls -la'",
    "which python3",
    "type -a python",
    "nohup python server.py &",
    "jobs -l",
    "fg %1",
    "kill %2",
    "watch -n 2 kubectl get pods",
    "xargs -P4 -I{} sh -c '...' -- {}",
]


# ---------------------------------------------------------------------------
# Partial-input generator
# ---------------------------------------------------------------------------

def partials_for(command: str) -> List[Tuple[str, str]]:
    """Return several (partial, full) pairs for a single full command."""
    tokens = command.split()
    pairs: List[Tuple[str, str]] = []

    # 1. Progressively longer token-aligned prefixes
    for n in range(1, len(tokens)):
        prefix = " ".join(tokens[:n])
        # Only include if prefix is meaningfully shorter
        if len(prefix) < len(command) - 1:
            pairs.append((prefix, command))
        # Also try prefix + trailing space
        if n < len(tokens):
            pairs.append((prefix + " ", command))

    # 2. Character-level partial of the last token (50% and 75% depth)
    if len(tokens) >= 2:
        base = " ".join(tokens[:-1]) + " "
        last = tokens[-1]
        for frac in (0.5, 0.75):
            cut = max(1, int(len(last) * frac))
            pairs.append((base + last[:cut], command))

    # 3. Full command minus 1–3 trailing characters
    for drop in (1, 2, 3):
        if len(command) > drop + 3:
            pairs.append((command[:-drop], command))

    # Deduplicate and filter out trivially useless pairs
    seen: set = set()
    result: List[Tuple[str, str]] = []
    for inp, out in pairs:
        inp = inp.rstrip(" ") if not inp.endswith(" ") else inp
        if inp and inp not in seen and inp != out and len(inp) >= 2:
            seen.add(inp)
            result.append((inp, out))

    return result


# ---------------------------------------------------------------------------
# Dataset assembly
# ---------------------------------------------------------------------------

def build_dataset() -> List[dict]:
    """Build the complete training dataset."""
    pairs: List[Tuple[str, str]] = []
    for cmd in FULL_COMMANDS:
        pairs.extend(partials_for(cmd))

    # Shuffle for better training distribution
    random.seed(42)
    random.shuffle(pairs)

    # Deduplicate by input
    seen_inputs: set = set()
    records: List[dict] = []
    for inp, out in pairs:
        if inp not in seen_inputs:
            seen_inputs.add(inp)
            records.append({"input": inp, "output": out})

    return records


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Generate shell command training data")
    parser.add_argument(
        "--output", "-o",
        default="src/training/zsh_training_data.jsonl",
        help="Output JSONL path",
    )
    parser.add_argument(
        "--max", "-m", type=int, default=0,
        help="Max examples (0 = unlimited)",
    )
    args = parser.parse_args()

    records = build_dataset()
    if args.max:
        records = records[: args.max]

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")

    print(f"Generated {len(records)} training examples → {out_path}")
    print(f"Unique full commands: {len(FULL_COMMANDS)}")


if __name__ == "__main__":
    main()
