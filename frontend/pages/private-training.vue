<script setup lang="ts">
const api = useGymApi()
const [{ data: slots }, { data: bookings }] = await Promise.all([
  useAsyncData("private-slots", () => api.getPrivateSlots()),
  useAsyncData("bookings", () => api.getBookings()),
])
</script>

<template>
  <section class="panel">
    <h2>私教空闲时段</h2>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>教练</th>
            <th>开始</th>
            <th>结束</th>
            <th>时长</th>
            <th>是否被预约</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="slot in slots || []" :key="slot.id">
            <td>{{ slot.coachName }}</td>
            <td>{{ slot.startAt }}</td>
            <td>{{ slot.endAt }}</td>
            <td>{{ slot.durationMinutes }} 分钟</td>
            <td>{{ slot.booked ? "已预约" : "可预约" }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>

  <section class="panel">
    <h2>预约记录</h2>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>会员</th>
            <th>课程</th>
            <th>类型</th>
            <th>预约时间</th>
            <th>签到</th>
            <th>扣次状态</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in bookings || []" :key="item.id">
            <td>{{ item.memberName }}</td>
            <td>{{ item.courseName }}</td>
            <td>{{ item.bookingType }}</td>
            <td>{{ item.bookedAt }}</td>
            <td>{{ item.signedIn ? "已签到" : "未签到" }}</td>
            <td>{{ item.deductionDone ? "已扣次" : "待扣次" }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
