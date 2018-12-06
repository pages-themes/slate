---
layout: default
---

# Assignment #2

---
# Setup
- Recommendation
    - [OpenCV](https://opencv.org/) : **3.4.0**
    - OS : Windows 10
    - Visual Studio 2015  
    - [SourceTree](https://www.sourcetreeapp.com/)
  
- C++ & OpenCV를 이용하여 작성 ([OpenCV Tutorial](https://docs.google.com/presentation/d/1Uv1geoOMUp7PI4ReuiN8SLE4I6BZglN1viCBqW3DB8Y/edit))
- Github 활용 ([Github Tutorial](https://opentutorials.org/course/2708))
  
---

# 작업 방법 (변경됨!)

## Step 1. [IPCVLabEdu의 issues](https://github.com/IPCVLabEdu/assignments/issues)에 이슈 작성  
- New issue 버튼을 누르면 이슈를 작성할 수 있음 
- {이름} assignment 2 라고 작성 (필수)
- 오른쪽 Assignees 에 본인 아이디 등록 (필수)
- 오른쪽 Labels에 assignment 태그 등록 (필수)
- 본인 이슈의 이슈넘버 확인 (필수, git commit 메세지에 항상 추가할 것임) 

![image](https://user-images.githubusercontent.com/15168540/49554485-c0574200-f93f-11e8-9d48-84d15a0d31f7.png)
예시(이 경우 `#13`이 이슈넘버)

## Step 2. Upstream에서 assignment2 가져오기 
- Source Tree에서 왼쪽 창에 `원격` - `Upstream` 우클릭 후 `Upstream 가져오기`
- `Upstream 가져오기`를 하면 `Upstream/assignment_2`가 새로 생길 것임 
  
## Step 3. 내 브랜치에 assignment2 머지하기 
- `{내 계정}_ass1`로 `checkout` (더블클릭으로 이동)
- (앞으로 기존의 `{내 계정}_ass1` 브랜치를 계속 사용할 것임)
- `{내 계정}_ass1`이 선택 된 상태에서 `assignment_2`가 위치한 노드에 `병합(merge)` 
- 병합이 이상없이 완료되면 프로젝트 실행 후 과제 진행 
- 병합 시 충돌이 발생하는 경우 

## Step 4. 결과 영상은 이슈의 comment로 등록 
- Step 1. 에서 개인이 작성한 이슈에 **반드시** 결과 영상을 업로드해 주시기 바랍니다. 
- 영상을 업로드하는 방법은 간단합니다. 

![image](https://user-images.githubusercontent.com/15168540/49555057-b46c7f80-f941-11e8-8649-262e24c4d589.png)

- 그림처럼 작성란에 이미지를 `드래그 & 드롭` 하거나, 이미지로 `ctrl+c`+ `ctrl+v`가 가능합니다. 
- Markdown을 지원합니다. 
- [예시](https://github.com/IPCVLabEdu/assignments/issues/16)

## Step 5. 기타
과제 중 발생하는 버그, 질문, 논의사항 등을 **[github issues](https://github.com/IPCVLabEdu/assignments/issues)** 채널을 적극적으로 활용해 주시기 바랍니다. 이슈 작성 시 질문은 question, 버그는 bugs, 논의사항은 discussion 등 적절한 label을 달아주시기 바랍니다.  

# Git Commit 메세지 작성 관련 

- Commit 메세지 작성은 상당히 중요합니다.  
- 이런 식의 커밋 메세지는 앞으로 곤란합니다. ~~죽는다~~ ![image](https://user-images.githubusercontent.com/15168540/49555134-1e852480-f942-11e8-9d2d-8eb81f45574b.png)

- 간단한 규칙을 추가하겠습니다.  
> 1. 커밋 메세지에 이슈넘버를 추가합니다. **(필수!)**   
 예시 : #16:공백
![image](https://user-images.githubusercontent.com/15168540/49555280-af5c0000-f942-11e8-8872-0bb49b823838.png)
> 2. 과제를 다 끝내고 커밋을 한번 하는게 아니라, 구현 단위로 의미있는 커밋 메세지 남기기 (1커밋 1기능) **(필수!)** 
> - 이는 경험이 많이 필요합니다. 따라서 많은 고민을 하고 레퍼런스를 찾아보시기 바람  
> 3. 커밋 메세지는 영어로 작성 **(권고)**

[훌륭한 Git 커밋 메시지의 일곱 가지 규칙](https://item4.github.io/2016-11-01/How-to-Write-a-Git-Commit-Message/) **(권고)**  
>1. 제목과 본문을 빈 행으로 분리한다  
>2. 제목 행을 50자로 제한한다  
>3. 제목 행 첫 글자는 대문자로 쓴다  
>4. 제목 행 끝에 마침표를 넣지 않는다  
>5. 제목 행에 명령문을 사용한다  
>6. 본문을 72자 단위로 개행한다  
>7. 어떻게 보다는 무엇과 왜를 설명한다  

# 과제 제출방법 
1. 우선 local/{본인이름_ass1}으로 과제 진행
2. origin/{본인이름_ass1} 으로 push
3. origin/{본인이름_ass1} -> upstream/{본인이름_ass1} 으로 Pull Request 
4. 각자 배정된 Reviewer에게 review 받은 후 merge 후 과제 종료 

---

### 과제에 앞서 과제에 사용할 적절한 이미지를 구합니다. 
1. sample2_0.bmp : 이진화 입력 이미지 (grayscale)
2. sample2_1.bmp : 이진화 입력 이미지 (grayscale)
3. sample2_2_1.bmp : 64 x 64 의 작은 이미지   
  **-> 4way, 8way floodfill의 결과의 차이를 보여야 함**
4. sample2_2_2.bmp : 640 x 640 의 큰 이미지 

# Q0 : 영상 이진화 알고리즘 구현 
>**assignment2_0.cpp** 를 수행합니다.

![image](https://user-images.githubusercontent.com/15168540/49555725-3198f400-f944-11e8-9b16-f6d65ad3db63.png)


# **Result**  
구현이 맞다면, OpenCV에서 제공하는 이진화 알고리즘과
구현한 이진화 알고리즘의 결과가 같아야 합니다. 
error는 소숫점 2째자리 까지 허용하지만 0이 될 수도 있습니다. 

```console
error: 0
PASS!!!
```

![image](https://user-images.githubusercontent.com/15168540/49555777-7755bc80-f944-11e8-9691-42b3a62a6e31.png)

# Q1 : 오츄 알고리즘(효율적인 버전)
>**assignment2_1.cpp** 를 수행합니다.

![image](https://user-images.githubusercontent.com/15168540/49556058-84bf7680-f945-11e8-8679-dd0f23675f03.png)

# **Result**  
구현 알고리즘과 OpenCV에서 제공하는 오츄 알고리즘의 결과를 비교합니다. 
구현이 맞다면 결과가 같아야 합니다. 
error는 소숫점 2째자리 까지 허용하지만 잘 구현하면 error = 0 입니다. 
![image](https://user-images.githubusercontent.com/15168540/49556046-77a28780-f945-11e8-8ada-7cda19fcf65a.png)


```console
error: 0
PASS!!!
```

# Q2 : Floodfill 알고리즘 
>**assignment2_2.cpp** 를 수행합니다.

![image](https://user-images.githubusercontent.com/15168540/49556838-e503e780-f948-11e8-8fb0-51d1a228e1fc.png)


![image](https://user-images.githubusercontent.com/15168540/49556830-de757000-f948-11e8-960e-80874a6843e4.png)

![image](https://user-images.githubusercontent.com/15168540/49556842-e7fed800-f948-11e8-844a-a964b6b26075.png)

# **Result**  
![image](https://user-images.githubusercontent.com/15168540/49556809-ca317300-f948-11e8-9760-e26a6353cb1d.png)

![image](https://user-images.githubusercontent.com/15168540/49556818-d1588100-f948-11e8-96b4-2260b5934a9e.png)
