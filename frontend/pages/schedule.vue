<script setup lang="ts">
const api = useGymApi()
const { data: schedule } = await useAsyncData("schedule", () => api.getSchedule())

const weekdayMap: Record<number, string> = {
  1: "周一",
  2: "周二",
  3: "周三",
  4: "周四",
  5: "周五",
  6: "周六",
  7: "周日",
}
</script>

<template>
  <section class="panel">
    <h2>团课课表</h2>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>星期</th>
            <th>时间段</th>
            <th>课程</th>
            <th>教练</th>
            <th>教室</th>
            <th>已约/容量</th>
            <th>状态</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in schedule || []" :key="item.id">
            <td>{{ weekdayMap[item.weekday] }}</td>
            <td>{{ item.startAt }} - {{ item.endAt }}</td>
            <td>{{ item.courseName }}</td>
            <td>{{ item.coachName }}</td>
            <td>{{ item.roomName }}</td>
            <td>{{ item.booked }}/{{ item.capacity }}</td>
            <td>{{ item.status }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
