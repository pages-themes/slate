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
<br/>  
## 결과 제출   
 **결과 제출은 [여기](http://visual.kangwon.ac.kr/assignment)를 눌러주세요.**


[이전](../../)
