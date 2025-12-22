<div class="row mb-3">
    <div class="col-md-4">
        <label class="form-label">基地面積 (m²)</label>
        </div>

    <div class="col-md-4">
        <label class="form-label">總樓地板面積 (m²)</label>
        </div>

    </div>

<h5 class="mt-4"><i class="bi bi-building"></i> 地上/地下層數設定</h5> <div class="row mb-3">
    <div class="col-md-4">
        <label class="form-label">地上層數 (F)</label>
        <div class="input-group">
             </div>
    </div>

    <div class="col-md-4">
        <label class="form-label">屋突層數 (R)</label>
        <div class="input-group">
            </div>
    </div>

    <div class="col-md-4">
        <label class="form-label">地下層數 (B)</label>
        <div class="input-group">
            <button class="btn btn-outline-secondary" type="button" @click="decrement('basementFloors')">-</button>
            <input type="number" class="form-control text-center" v-model.number="projectData.basementFloors">
            <button class="btn btn-outline-secondary" type="button" @click="increment('basementFloors')">+</button>
        </div>
        <div class="form-check mt-2">
            <input class="form-check-input" type="checkbox" id="soilControl" v-model="projectData.soilControl">
            <label class="form-check-label" for="soilControl">
                評估土方運棄管制?
            </label>
        </div>
    </div>
</div>