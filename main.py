# -*- coding: utf-8 -*-
import argparse
import os
from github import Github

MD_HEAD = """## GitBlog

我的个人博客，使用 GitHub Issues 和 GitHub Actions 自动生成。

"""

BACKUP_DIR = "BACKUP"
ANCHOR_NUMBER = 5
IGNORE_LABELS = ["Top", "TODO", "Friends", "About", "Things"]


def get_me(user):
    return user.get_user().login


def is_me(issue, me):
    return issue.user.login == me


def format_time(time):
    return str(time)[:10]


def login(token):
    return Github(token)


def get_repo(user: Github, repo: str):
    return user.get_repo(repo)


def get_repo_labels(repo):
    """获取仓库所有标签"""
    return [l for l in repo.get_labels()]


def get_issues_from_label(repo, label):
    """根据标签获取 issues"""
    return repo.get_issues(labels=(label,))


def add_issue_info(issue, md):
    time = format_time(issue.created_at)
    md.write(f"- [{issue.title}]({issue.html_url}) - {time}\n")


def add_md_header(md, repo_name):
    with open(md, "w", encoding="utf-8") as md:
        md.write(MD_HEAD.format(repo_name=repo_name))
        md.write("\n")


def add_md_label(repo, md, me):
    """按标签分类添加 issues"""
    labels = get_repo_labels(repo)

    # 按描述信息排序标签，如果没有描述则按名称排序
    labels = sorted(
        labels,
        key=lambda x: (
            x.description is None,
            x.description == "",
            x.description,
            x.name,
        ),
    )

    with open(md, "a+", encoding="utf-8") as md:
        for label in labels:
            # 跳过忽略的标签
            if label.name in IGNORE_LABELS:
                continue

            issues = get_issues_from_label(repo, label)
            issues = list(sorted(issues, key=lambda x: x.created_at, reverse=True))
            if len(issues) != 0:
                md.write("## " + label.name + "\n\n")
            i = 0
            for issue in issues:
                if not issue:
                    continue
                if is_me(issue, me) and not issue.pull_request:
                    if i == ANCHOR_NUMBER:
                        md.write("<details><summary>显示更多</summary>\n")
                        md.write("\n")
                    add_issue_info(issue, md)
                    i += 1
            if i > ANCHOR_NUMBER:
                md.write("</details>\n")
                md.write("\n")


def add_md_issues(repo, md, me):
    """添加所有 issues，按创建时间倒序排列"""
    with open(md, "a+", encoding="utf-8") as md:
        try:
            md.write("## 所有文章\n\n")
            # 获取所有 issues，按创建时间倒序排列
            issues = list(repo.get_issues(sort="created", direction="desc", state="all"))
            
            for issue in issues:
                # 只显示自己创建的 issue，排除 pull request
                if is_me(issue, me) and not issue.pull_request:
                    add_issue_info(issue, md)
                    
        except Exception as e:
            print(f"Error adding issues: {str(e)}")


def get_to_generate_issues(repo, dir_name, issue_number=None):
    """获取需要生成备份文件的 issues"""
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)
        
    md_files = os.listdir(dir_name)
    generated_issues_numbers = [
        int(i.split("_")[0]) for i in md_files if i.split("_")[0].isdigit()
    ]
    
    to_generate_issues = [
        i
        for i in list(repo.get_issues(state="all"))
        if int(i.number) not in generated_issues_numbers
    ]
    
    if issue_number:
        try:
            to_generate_issues.append(repo.get_issue(int(issue_number)))
        except Exception as e:
            print(f"Error getting issue {issue_number}: {str(e)}")
            
    return to_generate_issues


def save_issue(issue, me, dir_name=BACKUP_DIR):
    """保存 issue 到备份文件"""
    # 清理文件名中的特殊字符
    safe_title = issue.title.replace('/', '-').replace(' ', '.').replace('?', '').replace(':', '').replace('*', '').replace('"', '').replace('<', '').replace('>', '').replace('|', '')
    md_name = os.path.join(dir_name, f"{issue.number}_{safe_title}.md")
    
    try:
        with open(md_name, "w", encoding="utf-8") as f:
            f.write(f"# [{issue.title}]({issue.html_url})\n\n")
            f.write(f"创建时间: {format_time(issue.created_at)}\n\n")
            f.write(issue.body or "")
            
            # 添加自己的评论
            if issue.comments:
                for c in issue.get_comments():
                    if is_me(c, me):
                        f.write("\n\n---\n\n")
                        f.write(c.body or "")
    except Exception as e:
        print(f"Error saving issue {issue.number}: {str(e)}")


def main(token, repo_name, issue_number=None, dir_name=BACKUP_DIR):
    try:
        user = login(token)
        me = get_me(user)
        repo = get_repo(user, repo_name)
        
        # 生成 README.md
        add_md_header("README.md", repo_name)
        add_md_label(repo, "README.md", me)
        add_md_issues(repo, "README.md", me)
        
        # 获取需要生成备份的 issues
        to_generate_issues = get_to_generate_issues(repo, dir_name, issue_number)
        
        # 保存 issues 到备份文件夹
        for issue in to_generate_issues:
            if is_me(issue, me) and not issue.pull_request:
                save_issue(issue, me, dir_name)
                
        print(f"Generated README.md and {len(to_generate_issues)} backup files")
        
    except Exception as e:
        print(f"Error in main: {str(e)}")


if __name__ == "__main__":
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
        
    parser = argparse.ArgumentParser()
    parser.add_argument("github_token", help="GitHub token")
    parser.add_argument("repo_name", help="Repository name (owner/repo)")
    parser.add_argument(
        "--issue_number", help="Specific issue number to process", default=None, required=False
    )
    
    options = parser.parse_args()
    main(options.github_token, options.repo_name, options.issue_number)